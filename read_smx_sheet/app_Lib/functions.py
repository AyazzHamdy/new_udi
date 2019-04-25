import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from read_smx_sheet.parameters import parameters as pm
import dask.dataframe as dd


def read_excel(file_path, sheet_name, filter=None, reserved_words_validation=None, nan_to_empty=True):
    try:
        df = pd.read_excel(file_path, sheet_name)
        df_cols = list(df.columns.values)
        df = df.applymap(lambda x: x.strip() if type(x) is str else x)

        if filter:
            df = df_filter(df, filter, False)

        if nan_to_empty:
            if isinstance(df, pd.DataFrame):
                df = replace_nan(df, '')
                df = df.applymap(lambda x: int(x) if type(x) is float else x)
            else:
                df = pd.DataFrame(columns=df_cols)


        if reserved_words_validation is not None:
            df = rename_sheet_reserved_word(df, reserved_words_validation[0], reserved_words_validation[1], reserved_words_validation[2])

        # save_sheet_data(df, file_path, sheet_name)
    except:
        df = pd.DataFrame()
    return df


def df_filter(df, filter=None, filter_index=True):
    if filter:
        for i in filter:
            if filter_index:
                df = df[df.index.isin(i[1])]
            else:
                df = df[df[i[0]].isin(i[1])]

    if not df.empty:
        return df


def replace_nan(df, replace_with):
    return df.replace(np.nan, replace_with, regex=True)


def is_Reserved_word(Supplements, Reserved_words_source, word):
    Reserved_words = Supplements[Supplements['Reserved words source'] == Reserved_words_source][['Reserved words']]
    is_Reserved_word = True if Reserved_words[Reserved_words['Reserved words'] == word]['Reserved words'].any() == word else False
    return is_Reserved_word


def rename_sheet_reserved_word(sheet_df, Supplements_df, Reserved_words_source, columns):
    if not sheet_df.empty:
        for col in columns:
            sheet_df[col] = sheet_df.apply(lambda row: rename_reserved_word(Supplements_df, Reserved_words_source, row[col]), axis=1)
    return sheet_df


def rename_reserved_word(Supplements, Reserved_words_source, word):
    return word + '_' if is_Reserved_word(Supplements, Reserved_words_source, word) else word


def get_file_name(file):
    return os.path.splitext(os.path.basename(file))[0]


def get_core_table_columns(Core_tables, Table_name ):
    Core_tables_df = Core_tables.loc[(Core_tables['Layer'] == 'CORE')
                                    & (Core_tables['Table name'] == Table_name)
                                    ].reset_index()
    return Core_tables_df


def get_core_tables(Core_tables):
    return Core_tables.loc[Core_tables['Layer'] == 'CORE'][['Table name', 'Fallback']].drop_duplicates()


def get_stg_tables(STG_tables, source_name=None):
    if source_name:
        stg_table_names = STG_tables.loc[STG_tables['Source system name'] == source_name][['Table name', 'Fallback']].drop_duplicates()
    else:
        stg_table_names = STG_tables[['Table name', 'Fallback']].drop_duplicates()
    return stg_table_names


def get_stg_table_nonNK_columns(STG_tables, source_name, Table_name, with_sk_columns=False):
    STG_tables_df = STG_tables.loc[(STG_tables['Source system name'] == source_name)
                                   & (STG_tables['Table name'] == Table_name)
                                   & (STG_tables['Natural key'].isnull())
                                   ].reset_index()
    return STG_tables_df


def get_stg_table_columns(STG_tables, source_name, Table_name, with_sk_columns=False):
    if source_name:
        STG_tables_df = STG_tables.loc[(STG_tables['Source system name'] == source_name)
                                        & (STG_tables['Table name'] == Table_name)
                                       ].reset_index()
    else:
        STG_tables_df = STG_tables.loc[STG_tables['Table name'] == Table_name].reset_index()

    if not with_sk_columns:
        STG_tables_df = STG_tables_df.loc[(STG_tables_df['Key set name'] == '')
                                          & (STG_tables_df['Code set name'] == '')
                                          ].reset_index()

    # print(STG_tables_df)
    return STG_tables_df


def single_quotes(string):
    return "'%s'" % string


def assertions(table_maping_row,Core_tables_list):
    assert (table_maping_row['Main source'] != None), 'Missing Main Source  for Table Mapping:{}'.format(
        str(table_maping_row['Mapping name']))
    assert (table_maping_row[
                'Target table name'] in Core_tables_list), 'TARGET TABLE NAME not found in Core Tables Sheet for Table Mapping:{}'.format(
        str(table_maping_row['Mapping name']))


def list_to_string(list, separator=None, between_single_quotes=0):
    if separator is None:
        prefix = ""
    else:
        prefix = separator
    to_string = prefix.join((single_quotes(str(x)) if between_single_quotes == 1 else str(x)) if x is not None else "" for x in list)

    return to_string


def string_to_dict(sting_dict, separator=' '):
    if sting_dict:
        # ex: Firstname="Sita" Lastname="Sharma" Age=22 Phone=1234567890
        return eval("dict(%s)" % ','.join(sting_dict.split(separator)))


def wait_for_processes_to_finish(processes_numbers, processes_run_status, processes_names):
    count_finished_processes = 0
    no_of_subprocess = len(processes_numbers)

    while processes_numbers:
        for p_no in range(no_of_subprocess):
            if processes_run_status[p_no].poll() is not None:
                try:
                    processes_numbers.remove(p_no)
                    count_finished_processes += 1
                    # print('-----------------------------------------------------------')
                    # print('\nProcess no.', p_no, 'finished, total finished', count_finished_processes, 'out of', no_of_subprocess)
                    print(count_finished_processes, 'out of', no_of_subprocess, 'finished.\t', processes_names[p_no])
                except:
                    pass


def xstr(s):
    if s is None:
        return ''
    return str(s)


def save_to_parquet(pq_df, dataset_root_path, partition_cols=None, string_columns=None):
    if not pq_df.empty:

        # all_object_columns = df.select_dtypes(include='object').columns
        # print(all_object_columns)

        if string_columns is None:
            # string_columns = df.columns
            string_columns = pq_df.select_dtypes(include='object').columns


        for i in string_columns:
            pq_df[i] = pq_df[i].apply(xstr)

        partial_results_table = pa.Table.from_pandas(df=pq_df, nthreads=None)

        pq.write_to_dataset(partial_results_table, root_path=dataset_root_path, partition_cols=partition_cols,
                            use_dictionary=False
                            )
        # flavor = 'spark'
        # print("{:,}".format(len(df.index)), 'records inserted into', dataset_root_path, 'in', datetime.datetime.now() - start_time)


def read_all_from_parquet(dataset, columns, use_threads, filter=None):
    try:
        df = pq.read_table(dataset,
                           columns=columns,
                           use_threads=use_threads,
                           use_pandas_metadata=True).to_pandas()

        if filter:
            df = df_filter(df, filter, False)
    except:
        df = pd.DataFrame()

    return df


def read_all_from_parquet_delayed(dataset, columns=None, filter=None):
    df = dd.read_parquet(path=dataset, columns=columns, engine='pyarrow')
    if filter:
        for i in filter:
            df = df[df[i[0]].isin(i[1])]
    return df


def get_sheet_path(smx_file_path, output_path, sheet_name):
    file_name = get_file_name(smx_file_path)
    parquet_path = output_path + "/" + file_name + "/" + pm.parquet_db_name + "/" + sheet_name
    return parquet_path


def save_sheet_data(df, smx_file_path, output_path, sheet_name):
    parquet_path = get_sheet_path(smx_file_path, output_path, sheet_name)
    save_to_parquet(df, parquet_path, partition_cols=None, string_columns=None)


def get_sheet_data(smx_file_path, output_path, sheet_name, df_filter=None):
    parquet_path = get_sheet_path(smx_file_path, output_path, sheet_name)
    df_sheet = read_all_from_parquet(parquet_path, None, True, filter=df_filter)
    return df_sheet