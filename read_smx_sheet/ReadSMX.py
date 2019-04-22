import os
import sys
sys.path.append(os.getcwd())
from app_Lib import manage_directories as md, functions as funcs
from dask import compute, delayed
# from dask.diagnostics import ProgressBar
# import traceback
import datetime as dt
import multiprocessing
from templates import gcfr, D003, D002, D210, D300, D320, D420, D000, D001, D200, D330, D340, D400,D410,D415, D615, D600, D607, D608, D610,D620, D630, D640


class ReadSmx:
    def __init__(self):
        self.parallel_read_smx_source = []
        self.parallel_create_output_source_path = []
        self.parallel_build_scripts = []
        self.parallel_templates = []
        # self.count_smx = 0
        # self.count_sources = 0

    def read_smx_sheet(self, home_output_path, smx_file_path):
        start_time = dt.datetime.now()
        # print("\nStart processing: ", smx_file_path)
        count_sources = 0
        try:
            System = funcs.read_excel(smx_file_path, sheet_name='System')
            teradata_sources = System[System['Source type'] == 'TERADATA']
            count_sources = count_sources + len(teradata_sources.index)

            Supplements = delayed(funcs.read_excel)(smx_file_path, sheet_name='Supplements')
            Column_mapping = delayed(funcs.read_excel)(smx_file_path, sheet_name='Column mapping')
            BMAP_values = delayed(funcs.read_excel)(smx_file_path, sheet_name='BMAP values')
            BMAP = delayed(funcs.read_excel)(smx_file_path, sheet_name='BMAP')
            BKEY = delayed(funcs.read_excel)(smx_file_path, sheet_name='BKEY')
            Core_tables = delayed(funcs.read_excel)(smx_file_path, sheet_name='Core tables')
            Core_tables = delayed(funcs.rename_sheet_reserved_word)(Core_tables, Supplements, 'TERADATA', ['Column name', 'Table name'])

            delayed_read_smx_source = delayed(self.read_smx_source)(home_output_path, smx_file_path, teradata_sources, Supplements, Column_mapping, BMAP_values, BMAP, BKEY, Core_tables)
            self.parallel_read_smx_source.append(delayed_read_smx_source)

            if len(self.parallel_read_smx_source) > 0:
                cpu_count = multiprocessing.cpu_count()
                compute(*self.parallel_read_smx_source, num_workers=cpu_count)
                compute(*self.parallel_create_output_source_path, num_workers=cpu_count)
                compute(*self.parallel_build_scripts, num_workers=cpu_count)
                compute(*self.parallel_templates, num_workers=cpu_count)

        except:
            pass
            # self.count_smx = self.count_smx - 1
        end_time = dt.datetime.now()
        # print("\nProcessing: ", smx_file_path, " completed, elapsed time ", end_time-start_time)

    def read_smx_source(self, home_output_path, smx_file_path, teradata_sources, Supplements, Column_mapping, BMAP_values, BMAP, BKEY, Core_tables):
        for system_index, system_row in teradata_sources.iterrows():
            try:
                Loading_Type = system_row['Loading type'].upper()
                source_name = system_row['Source system name']

                source_output_path = home_output_path + "/" + Loading_Type + "/" + source_name
                delayed_create_source_output_path = delayed(md.create_folder)(source_output_path)
                self.parallel_create_output_source_path.append(delayed_create_source_output_path)

                source_name_filter = [['Source', [source_name]]]
                stg_source_name_filter = [['Source system name', [source_name]]]

                Table_mapping = delayed(funcs.read_excel)(smx_file_path, 'Table mapping', source_name_filter, False)

                STG_tables = delayed(funcs.read_excel)(smx_file_path, 'STG tables', stg_source_name_filter, False)
                STG_tables = delayed(funcs.rename_sheet_reserved_word)(STG_tables, Supplements, 'TERADATA', ['Column name', 'Table name'])

                delayed_build_scripts = delayed(self.build_scripts)(source_output_path, source_name, Loading_Type, Table_mapping, STG_tables, BKEY, Core_tables, BMAP, BMAP_values, Column_mapping)
                self.parallel_build_scripts.append(delayed_build_scripts)

            except Exception as error:
                # print(error)
                # traceback.print_exc()
                self.count_sources = self.count_sources - 1

    def build_scripts(self, source_output_path, source_name, Loading_Type, Table_mapping, STG_tables, BKEY, Core_tables, BMAP, BMAP_values, Column_mapping):

        self.parallel_templates.append(delayed(D000.d000)(source_output_path, source_name, Table_mapping, STG_tables, BKEY))
        self.parallel_templates.append(delayed(D001.d001)(source_output_path, source_name, STG_tables))
        self.parallel_templates.append(delayed(D002.d002)(source_output_path, Core_tables, Table_mapping))
        self.parallel_templates.append(delayed(D003.d003)(source_output_path, BMAP_values, BMAP))

        self.parallel_templates.append(delayed(D200.d200)(source_output_path, STG_tables))
        self.parallel_templates.append(delayed(D210.d210)(source_output_path, STG_tables))

        self.parallel_templates.append(delayed(D300.d300)(source_output_path, STG_tables, BKEY))
        self.parallel_templates.append(delayed(D320.d320)(source_output_path, STG_tables, BKEY))
        self.parallel_templates.append(delayed(D330.d330)(source_output_path, STG_tables, BKEY))
        self.parallel_templates.append(delayed(D340.d340)(source_output_path, STG_tables, BKEY))

        self.parallel_templates.append(delayed(D400.d400)(source_output_path, STG_tables))
        self.parallel_templates.append(delayed(D410.d410)(source_output_path, STG_tables))
        self.parallel_templates.append(delayed(D415.d415)(source_output_path, STG_tables))
        self.parallel_templates.append(delayed(D420.d420)(source_output_path, STG_tables, BKEY, BMAP))

        self.parallel_templates.append(delayed(D600.d600)(source_output_path, Table_mapping, Core_tables))
        self.parallel_templates.append(delayed(D607.d607)(source_output_path, Core_tables, BMAP_values))
        self.parallel_templates.append(delayed(D608.d608)(source_output_path, Core_tables, BMAP_values))
        self.parallel_templates.append(delayed(D610.d610)(source_output_path, Table_mapping))
        self.parallel_templates.append(delayed(D615.d615)(source_output_path, Core_tables))
        self.parallel_templates.append(delayed(D620.d620)(source_output_path, Table_mapping, Column_mapping, Core_tables, Loading_Type))
        self.parallel_templates.append(delayed(D630.d630)(source_output_path, Table_mapping))
        self.parallel_templates.append(delayed(D640.d640)(source_output_path, source_name, Table_mapping))

    def validate_smx_sheet(self):
        pass


if __name__ == '__main__':
    read_smx = ReadSmx()
    inputs = funcs.string_to_dict(sys.argv[1])
    home_output_path = inputs['home_output_path']
    smx_file_path = inputs['smx_file_path']
    read_smx.read_smx_sheet(home_output_path, smx_file_path)