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
    _order_ = 'self spouse children family declined'
    self = 'Self'
    spouse = 'w/Spouse'
    children = 'w/Children'
    family = 'w/Family'
    declined = 'Declined'
IC = InsuranceChoice

class MedicalInsuranceChoice(fields.SelectionEnum):
    _order_ = 'self spouse children family declined'
    self = 'Self'
    spouse = 'w/Spouse'
    children = 'w/Children'
    family = 'w/Family'
    declined = 'Declined'
MIC = MedicalInsuranceChoice

class InsuranceDependent(fields.SelectionEnum):
    _order_ = 'spouse partner child'
    spouse = 'Spouse'
    partner = 'Domestic Partner'
    child = 'Child'
ID = InsuranceDependent

class FlexibleSpendingAccountChoice(fields.SelectionEnum):
    _order_ = 'medical child both none'
    medical = 'Medical'
    child = 'Child Care'
    both = 'Medical & Child Care'
    none = 'None'
FSAChoice = FlexibleSpendingAccountChoice

class FourZeroOneK(fields.SelectionEnum):
    _order_ = 'fixed percent none'
    fixed = 'Fixed'
    percent = 'Percent'
    none = 'None'

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

class hr_insurance_dependents(osv.Model):
    "insurance dependents of employee"
    _name = 'hr.insurance.dependent'
    _order = 'dob'

    _columns = {
        'name': fields.char('Name', size=128),
        'relation': fields.selection(InsuranceDependent, 'Dependents'),
        'dob': fields.date('Birth Date'),
        'ssn': fields.char('SSN', size=12),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'note': fields.text('Notes'),
        }

class hr_insurance_hr_employee(osv.Model):
    "add fields to hr.employee to track insurance choices over time"
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'hr_insurance_choice_ids': fields.one2many(
            'hr.insurance.employee_choice', 'employee_id',
            string='Insurance',
            ),
        'hr_insurance_dependents_ids': fields.one2many(
            'hr.insurance.dependent', 'employee_id',
            string='Dependents',
            ),
        'hr_insurance_dependents_note': fields.text('Notes'),
        'hr_insurance_fsa_choice': fields.selection(
            FSAChoice,
            string='Flexible Spending Account',
            ),
        'hr_insurance_fsa_amount': fields.float(string='FSA Amount'),
        'hr_insurance_fsa_eff_date': fields.date('FSA Effective Date'),
        'hr_insurance_401k_choice': fields.selection(
            FourZeroOneK,
            string='401k Contributions',
            ),
        'hr_insurance_401k_fixed_amount': fields.float(string='401k Fixed Amount'),
        'hr_insurance_401k_percent_amount': fields.float(string='401k Percent Amount'),
        'hr_insurance_401k_eff_date': fields.date('401k Effective Date'),
        # rest of fields currently unused
        'hr_insurance_year': fields.integer('Effective Year'),
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
        }

    fields.apply_groups(
            _columns,
            {
                'base.group_hr_manager' : ['hr_insurance_.*'],
                })

    def change_fsa(self, cr, uid, ids, choice, context=None):
        "user changed fsa selection"
        if choice in (False, 'none'):
            # no action needed
            return True
        else:
            # clear out other fsa fields
            return {
                'value': {
                        'hr_insurance_fsa_amount': False,
                        'hr_insurance_fsa_eff_date': False,
                        }}

    def change_401k(self, cr, uid, ids, choice, context=None):
        "user changed 401k selection"
        if choice in (False, 'none'):
            # no action needed
            return True
        else:
            # clear out other 401k fields
            return {
                'value': {
                        'hr_insurance_401k_fixed_amount': False,
                        'hr_insurance_401k_percent_amount': False,
                        'hr_insurance_401k_eff_date': False,
                        }}


class hr_insurance_employee_choice(osv.Model):
    "track yearly choices for insurance coverage"
    _name = 'hr.insurance.employee_choice'
    _order = 'year_month desc'

    def _calc_effective_date(self, cr, uid, ids, name, args, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%4d-%02d' % (rec.year, rec.month)
        return res

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='cascade'),
        'year_month': fields.char('Year-Month', required=True, size=7, oldname='year'),
        'medical': fields.selection(MedicalInsuranceChoice, 'Medical'),
        'dental': fields.selection(InsuranceChoice, 'Dental'),
        'vision': fields.selection(InsuranceChoice, 'Vision'),
        'life': fields.selection(InsuranceChoice, 'Life'),
        'note': fields.text('Notes'),
        }

    def default_get(self, cr, uid, fields_list, context=None):
        result = super(hr_insurance_employee_choice, self).default_get(cr, uid, fields_list, context=context)
        today = date(fields.date.context_today(self, cr, uid, context=context)).replace(delta_month=+1)
        year_month = today.strftime('%Y-%m')
        medical = dental = vision = life = False
        employee_id = context.get('default_employee_id')
        if employee_id is not None:
            records = self.read(cr, uid, [('employee_id','=',employee_id)])
            if records:
                records.sort(key=lambda r: r['year_month'])
                record = records[-1]
                medical = record['medical']
                dental = record['dental']
                vision = record['vision']
                life = record['life']
                new_date = date(record['year_month'], '%Y-%m').replace(delta_month=+1)
                if new_date > today:
                    year_month = new_date.strftime('%Y-%m')
        if 'year_month' in fields_list:
            result['year_month'] = year_month
        if 'medical' in fields_list:
            result['medical'] = medical
        if 'dental' in fields_list:
            result['dental'] = dental
        if 'vision' in fields_list:
            result['vision'] = vision
        if 'life' in fields_list:
            result['life'] = life
        return result

    def change_date(self, cr, uid, ids, ym, context=None):
        print ym
        if not ym:
            return True
        # did we get year/mo, year-mo, year mo, just year, or garbage?
        try:
            for sep in '/- ':
                if sep in ym:
                    year, month = ym.split(sep)
                    break
            else:
                year = ym
                month = '1'
            year = int(year)
            month = int(month)
            ym = date(year, month, 1)
            ym_text = ym.strftime('%Y-%m')
        except Exception, exc:
            _logger.error('Exception raised: %r', exc)
            return {
                'warning': {
                    'title': 'Bad date',
                    'message': 'Unable to evaluate %r\n' % (ym, ),
                    },
                }
        today = date(fields.date.context_today(self, cr, uid, context=context))
        min_year = today.year - 3
        max_year = today.year + 3
        if min_year <= ym.year <= max_year:
            return {
                'value': {
                    'year_month': ym_text,
                    }
                }
        else:
            return {
                'warning': {
                    'title': 'Out of range error',
                    'message': '%s is not between %r and %r\n' % (ym_text, min_year, max_year),
                    },
                }
