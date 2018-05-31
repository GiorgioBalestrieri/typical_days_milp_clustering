import numpy as np
from pyomo import environ as pe

def create_model(preserve_total_values=False, preserve_peak_values=False):
    
    m = pe.AbstractModel()
    
    #===================================
    #             Options
    #===================================
    
    m.options = dict(
        preserve_total_values = preserve_total_values,
        preserve_peak_values  = preserve_peak_values
    )
    
    def _apply_options(m):
        '''
        BuildAction used to apply options by (de)activating 
        constraints and (un)fixing variables.
        '''
        if not m.options['preserve_total_values']:
            m.relative_error_upper.deactivate()
            m.relative_error_lower.deactivate()
        if not m.options['preserve_peak_values']:
            m.preserve_peak.deactivate()
            m.at_least_one_preserved.deactivate()
            m.w.fix(0)
                
    
    #===================================
    #           Model Parameters
    #===================================
    
    m.n_days = pe.Param(
        within=pe.PositiveIntegers,
        doc='''Number of days.'''
    )
    
    m.n_clusters = pe.Param(
        within=pe.PositiveIntegers,
        doc='''Number of clusters.'''
    )
    
    m.n_extreme_days = pe.Param(
        within=pe.NonNegativeIntegers,
        initialize=0,
        doc='''Number of extreme days.'''
    )
    
    #====================================#
    #                 Sets
    #====================================#
    
    m.Days = pe.RangeSet(m.n_days)
    
    m.Days_cross = pe.Set(
        initialize=m.Days*m.Days,
        doc=''''''
    )
    
    m.Properties = pe.Set(doc='''Properties considered''')
    
    #====================================#
    #            Parameters
    #====================================#
    
    m.distance = pe.Param(m.Days_cross)
    
    m.x_daily_tot = pe.Param(
        m.Properties, m.Days,
        doc='''Total value of each property on each day.'''
    )
    
    m.x_daily_max = pe.Param(
        m.Properties, m.Days,
        mutable=True, # used to prevent errors in constraints
    )
    
    m.x_max = pe.Param(
        m.Properties,
        mutable = True, # used to prevent errors in constraints
        doc = '''Maximum overall values of each property.'''
    )
    
    def _x_total(m, p):
        return sum(m.x_daily_tot[p,i] for i in m.Days)
    
    m.x_total = pe.Param(
        m.Properties,
        initialize=_x_total,
        doc='''Total value of each property.'''
    )
    
    m.rel_tol = pe.Param(
        m.Properties,
        doc='''Relative error accepted for each property.'''
    )
    
    m.min_peak_share = pe.Param(
        m.Properties,
        doc = '''Minimum share of peak to be represented.'''
    )
    
    #====================================#
    #             Variables
    #====================================#
    
    m.z = pe.Var(
        m.Days_cross, 
        within = pe.Binary,
        initialize=0,
        doc = '''1 iff object j is assigned to the cluster 
        whose representative element is object i.'''
    )
    
    m.y = pe.Var(
        m.Days, 
        within = pe.Binary,
        initialize=0,
        doc = '''1 iff object i is chosen as representative 
        of its cluster.'''
    )
    
    #====================================#
    #         Auxiliary Variables
    #====================================#   
    
    def _x_weight(m, i):
        '''
        Returns the weight assigned to day i.
        First term: number of days it represents.
        Second term: 1 iff day i is extreme.
        '''
        n_days_represented = sum(m.z[i,j] for j in m.Days)
        extreme = 1 - sum(m.z[k,i] for k in m.Days)
        
        return n_days_represented + extreme
    
    m.x_weight = pe.Expression(
        m.Days,
        rule = _x_weight,
        doc = ''''''
    )
    
    def _x_total_estimated(m, p):
        '''Total estimated value of property p.'''
        return sum(m.x_weight[i] * m.x_daily_tot[p,i] for i in m.Days) 
    
    m.x_total_estimated = pe.Expression(
        m.Properties,
        rule = _x_total_estimated,
        doc = ''''''
    )
    
    def _chosen(m,i):
        '''Auxiliary. 1 iff day i is either typical or extreme.'''
        return m.y[i] + (1 - sum(m.z[i,j] for j in m.Days)) 
    
    m.chosen = pe.Expression(
        m.Days,
        rule = _chosen
    )
    
    m.w = pe.Var(
        m.Properties, m.Days,
        within = pe.Binary,
        doc='''Binary, used to impose that at least one chosen days 
        has a peak larger than a given proportion of the real peak.'''
    )
    
    #====================================#
    #             Constraints
    #====================================#
    
    def _total_representative_days(m):
        return sum(m.y[i] for i in m.Days) == m.n_clusters
    
    m.total_representative_days = pe.Constraint(
        rule = _total_representative_days,
        doc = '''One representative day for each cluster.'''
    )
    
    def _each_non_extreme_day_is_represented(m, j):
        return sum(m.z[i,j] for i in m.Days) <= 1
    
    m.each_non_extreme_day_is_represented = pe.Constraint(
        m.Days,
        rule = _each_non_extreme_day_is_represented,
        doc='''each day is represented by exactly 1 day 
        (without EDs)'''
    )
    
    def _total_represented_days(m):
        return sum(m.z[ij] for ij in m.Days_cross) == \
            m.n_days - m.n_extreme_days
    
    m.total_represented_days = pe.Constraint(
        rule = _total_represented_days,
        doc = '''All non-extreme days are represented.'''
    )
    
    def _represented_by_representative(m, i, j):
        return m.z[i,j] <= m.y[i]
    
    m.represented_by_representative = pe.Constraint(
        m.Days_cross,
        rule = _represented_by_representative,
        doc = '''Days can only be represented by 
        representative days.'''
    )
    
    #===================================
    #       Auxiliary Constraints
    #===================================
    
    def _relative_error_upper(m, p):
        return m.x_total_estimated[p] <= \
            (1 + m.rel_tol[p]) * m.x_total[p]
        
    m.relative_error_upper = pe.Constraint(
        m.Properties,
        rule=_relative_error_upper,
        doc=''''''
    )
    
    def _relative_error_lower(m, p):
        return m.x_total_estimated[p] >= \
            (1 - m.rel_tol[p]) * m.x_total[p]
        
    m.relative_error_lower = pe.Constraint(
        m.Properties,
        rule=_relative_error_lower,
        doc=''''''
    )
    
    def _preserve_peak(m, p, i):
        return m.x_daily_max[p,i] * m.chosen[i] - m.w[p,i] * m.min_peak_share[p] * m.x_max[p] >= 0
    
    m.preserve_peak = pe.Constraint(
        m.Properties,
        m.Days,
        rule=_preserve_peak,
        doc='''The day must be chosen and its max value
        must be larger than the overall peak.
        '''
    )
                         
    def _at_least_one_preserved(m, p):
        return sum(m.w[p,i] for i in m.Days) >= 1
    
    m.at_least_one_preserved = pe.Constraint(
        m.Properties,
        rule = _at_least_one_preserved,
        doc = '''Auxiliary. At least one of the days must 
        satisfy preserve_peak.'''
    )
    
    
    #====================================#
    #           Objective Function
    #====================================#
    
    def _total_distance(m):
        return sum(m.distance[ij]*m.z[ij] for ij in m.Days_cross)
    
    m.minimize_total_distance = pe.Objective(
        rule=_total_distance,
        doc='''Mininimize total distance between days 
        of the same cluster.'''        
    )
    
    
    # apply options
    m.apply_options = pe.BuildAction(rule=_apply_options)
    
    return m
    
    
    
    
    