"""
tables/fields needed:
    - insurance companies
        - name
        - medical
        - dental
        - vision
        - life
    - insurance rates
        - year
        - carrier
        - type
        - employee
        - spouse
        - children
        - family
    - insurance history
        - effective date
        - carrier
        - type
        - self
        - spouse
        - children
        - family
        - declined
    - employee
        link to insurance history
"""

import logging
from osv import osv, fields
from fnx import date

_logger = logging.getLogger(__name__)

class InsuranceType(fields.SelectionEnum):
    _order_ = 'medical dental vision life'
    medical = 'Medical'
    dental = 'Dental'
    vision = 'Vision'
    life = 'Life'
IT = InsuranceType

class InsuranceChoice(fields.SelectionEnum):
    self = 'Self'
    spouse = 'w/Spouse'
    children = 'w/Children'
    family = 'w/Family'
IC = InsuranceChoice

class MedicalInsuranceChoice(fields.SelectionEnum):
    self = 'Self'
    spouse = 'w/Spouse'
    children = 'w/Children'
    family = 'w/Family'
    declined = 'Declined'
MIC = MedicalInsuranceChoice

def nested_property(func):
    "make defining properties simpler (from Mike Muller) [fget, fset, fdel]"
    names = dict([(n, f) for n, f in func().items() if n in ('fset', 'fget', 'fdel')])
    names['doc'] = func.__doc__
    return property(**names)

class hr_insurance_company(osv.Model):
    _name = 'hr.insurance.company'

    def _offers_type(self, cr, uid, ids, field_names, arg, context=None):
        """
        returns True/False for each insurance type in field_names for each
        year in arg (default: all years)
        """
        hr_insurance_rate = self.pool.get('hr.insurance.rate')
        domain = [('company_id','in',ids),('type','in',field_names)]
        if arg:
            if not isinstance(arg, (list, tuple)):
                arg = [arg]
            domain.append(('year','in',arg))
        res = {}
        for id in ids:
            res[id] = dict.fromkeys(field_names, False)
        rates = hr_insurance_rate.read(
                cr, uid,
                ids=domain,
                fields=['year', 'type', 'company_id'],
                context=context,
                )
        for rate in rates:
            id = rate['company_id'][0]
            type = rate['type']
            print id, type
            res[id][type] = True
        return res

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner Record'),
        'name_related': fields.related('partner_id', 'name', string='Name', type='char'),
        # insurance categories and costs
        'medical': fields.function(
            _offers_type,
            type='boolean',
            string='Medical',
            multi='offers',
            ),
        'dental': fields.function(
            _offers_type,
            type='boolean',
            string='Dental',
            multi='offers',
            ),
        'vision': fields.function(
            _offers_type,
            type='boolean',
            string='Vision',
            multi='offers',
            ),
        'life': fields.function(
            _offers_type,
            type='boolean',
            string='Life',
            multi='offers',
            ),
        # rates
        'rate_ids': fields.one2many('hr.insurance.rate', 'company_id', 'Rates'),
        }

class hr_insurance_rate(osv.Model):
    _name = 'hr.insurance.rate'
    _order = 'year desc'

    _columns = {
        'year': fields.integer('Effective Year'),
        'company_id': fields.many2one('hr.insurance.company', 'Company'),
        'type': fields.selection(InsuranceType, 'Type'),
        'employee': fields.float('Employee cost'),
        'and_spouse': fields.float('with Spouse'),
        'and_children': fields.float('with Children'),
        'and_family': fields.float('with Family'),
        }

class hr_insurance_hr_employee(osv.Model):
    "add fields to hr.employee to track insurance choices over time"
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'hr_insurance_year': fields.integer('Effective Year', required=True),
        'hr_insurance_medical_self': fields.boolean('Medical - Self'),
        'hr_insurance_medical_spouse': fields.boolean('Medical - Spouse'),
        'hr_insurance_medical_children': fields.boolean('Medical - Children'),
        'hr_insurance_medical_declined': fields.boolean('Medical Declined'),
        'hr_insurance_dental_self': fields.boolean('Dental - Self'),
        'hr_insurance_dental_spouse': fields.boolean('Dental - Spouse'),
        'hr_insurance_dental_children': fields.boolean('Dental - Children'),
        'hr_insurance_vision_self': fields.boolean('Vision - Self'),
        'hr_insurance_vision_spouse': fields.boolean('Vision - Spouse'),
        'hr_insurance_vision_children': fields.boolean('Vision - Children'),
        'hr_insurance_life_self': fields.boolean('Life - Self'),
        'hr_insurance_life_spouse': fields.boolean('Life - Spouse'),
        'hr_insurance_life_children': fields.boolean('Life - Children'),
        'hr_insurance_choice_ids': fields.one2many(
            'hr.insurance.employee_choice', 'employee_id',
            string='Insurance',
            )
        }

class hr_insurance_employee_choice(osv.Model):
    "track yearly choices for insurance coverage"
    _name = 'hr.insurance.employee_choice'
    _order = 'year desc'

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'year': fields.integer('Year'),
        'medical': fields.selection(MedicalInsuranceChoice, 'Medical'),
        'dental': fields.selection(InsuranceChoice, 'Dental'),
        'vision': fields.selection(InsuranceChoice, 'Vision'),
        'life': fields.selection(InsuranceChoice, 'Life'),
        }

    def onchange_year(self, cr, uid, ids, year, context=None):
        today = date(fields.date.context_today(self, cr, uid, context=context))
        min_year = today.year - 3
        max_year = today.year + 3
        if min_year <= year <= max_year:
            return {}
        else:
            return {
                'warning': {
                    'title': 'Out of range error',
                    'message': 'Year %r is not between %r and %r' % (year, min_year, max_year),
                    },
                }
