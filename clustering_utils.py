import pandas as pd
from pyomo import environ as pe


def reindex_day_timestep(in_df):
    """
    Sets as index (multiindex) two columns with the day number (from 1)
    and the timestep number (from 1) within each day.
    Accepts as input a dataframe and returns a dataframe
    """
    
    out_df = in_df.copy()
    out_df['day'] = (out_df.groupby(pd.Grouper(freq='1d')).ngroup()+1 
                    ).reset_index(level=0, drop=True).values
    out_df['timestep'] = out_df.groupby('day').cumcount() + 1

    return out_df.set_index(['day', 'timestep'])


def extract_indexed_expression_values(indexed_expr):
    '''Returns the values of an indexed expression (PYOMO object).'''
    return dict((ind, pe.value(val)) for ind, val in indexed_expr.iteritems())


def get_pyomo_input_dictionary(data_dict, namespace=None):
    """
    - For all fields which are not dictionaries already (i.e. if they are not indexed), 
    it returns a dict like None:field.
    - it also returns the whole dictionary as namespace:dictionary, as required by PYOMO.
    """
    for k, v in data_dict.items():
        if not isinstance(v, dict):
            data_dict[k] = {None:v}
    
    return {namespace:data_dict}

def extract_results(model_instance):
    
    y = pd.Series(model_instance.y.get_values())
    z = pd.Series(model_instance.z.get_values()).unstack()
    
    return y,z
