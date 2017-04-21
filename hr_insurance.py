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
from openerp.exceptions import ERPError

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

    def onchange_hr_insurance(self, cr, uid, ids, type, field, choice_ids, year, value, context=None):
        print '-' * 50

        class YearlyRecord(object):

            def __init__(self, model, cr, uid, employee_id, year, record, fields=None):
                self.model = model
                self._record = self._medical = self._dental = self._vision = self._life = None
                self.employee_id = employee_id
                # print 'employee_id = %s' % (employee_id, )
                self.year = year
                # set self.record last
                self.record = record

            def __repr__(self):
                return '<YearlyRecord(employee_id=%r, year=%r)>' % (self.employee_id, self.year)

            @nested_property
            def medical():
                "medical choice"
                def fget(self):
                    return self._medical
                def fset(self, value):
                    self._medical = value
                return locals()

            @nested_property
            def dental():
                "dental choice"
                def fget(self):
                    return self._dental
                def fset(self, value):
                    self._dental = value
                return locals()

            @nested_property
            def vision():
                "vision choice"
                def fget(self):
                    return self._vision
                def fset(self, value):
                    self._vision = value
                return locals()

            @nested_property
            def life():
                "life choice"
                def fget(self):
                    return self._life
                def fset(self, value):
                    self._life = value
                return locals()

            @nested_property
            def mutable():
                "record of data changes"
                def fget(self):
                    mutable = {
                            'employee_id': self.employee_id,
                            'year': self.year,
                            'medical': self.medical,
                            'dental': self.dental,
                            'vision': self.vision,
                            'life': self.life,
                            }
                    if self.id is not None:
                        mutable['id'] = self.id
                    return mutable
                def fset(self, mutable):
                    for area in ('medical', 'dental', 'vision', 'life'):
                        setattr(self, area, mutable[area])
                    for attr in ('id', 'employee_id', 'year'):
                        if attr in mutable:
                            setattr(self, attr, mutable[attr])
                return locals()

            @nested_property
            def record():
                "write once, read many"
                def fget(self):
                    "return record accounting for any updates"
                    record = self._record
                    original, mutable = self.original, self.mutable
                    act, id, _ = record
                    if act == 0:
                        # new record
                        return [0, False, mutable.copy()]
                    elif act == 2:
                        return [2, self.id, False]
                    elif act in (1, 4):
                        if mutable == original:
                            return [4, self.id, False]
                        else:
                            return [1, self.id, dict([
                                (k, v)
                                for k, v in mutable.items()
                                if original[k] != v
                                ])]
                def fset(self, value):
                    if self._record is None:
                        self._record = value
                        act, id, new_data = value
                        if act == 0:
                            # new record
                            if not new_data:
                                new_data = {'medical': False, 'dental': False, 'vision': False, 'life': False}
                            original = new_data.copy()
                            mutable = new_data.copy()
                        elif act == 1:
                            # changing an existing record
                            [data] = self.model.pool.get('hr.insurance.employee_choice').read(cr, uid, [id])
                            original = data.copy()
                            mutable = data.copy()
                            mutable.update(new_data)
                        elif act == 2:
                            # delete record
                            original = {}
                            mutable = {}
                        elif act == 4:
                            # link to record
                            [data] = self.model.pool.get('hr.insurance.employee_choice').read(cr, uid, [id])
                            original = data.copy()
                            mutable = data.copy()
                        if 'year' in mutable:
                            self.year = mutable['year']
                        if mutable.get('employee_id'):
                            eid = mutable['employee_id']
                            if isinstance(eid, tuple):
                                # sometimes it's an int, othertimes an (int, str)
                                eid = eid[0]
                                if eid != self.employee_id:
                                    raise ERPError('ID mismatch', 'Employee id %r != %r' % (self.employee_id, mutable['employee_id']))
                        self.original = original
                        self.mutable = mutable
                        self.id = id
                return locals()


            YearlyRecord = vars()
            for type in ('medical', 'dental', 'vision', 'life'):
                for group in ('self', 'spouse', 'children', 'declined'):
                    insurance = '%s_%s' % (type, group)
                    master = '_%s' % (type, )
                    if type != 'medical' and group == 'declined':
                        continue
                    def _generic(type=type, master=master, group=group):
                        # key = (group, data)
                        adding = {
                                ('self', False): 'self',
                                ('spouse', False): 'spouse',
                                ('spouse', 'self'): 'spouse',
                                ('spouse', 'children'): 'family',
                                ('children', False): 'children',
                                ('children', 'self'): 'children',
                                ('children', 'spouse'): 'family',
                                }
                        if type == 'medical':
                            adding.update({
                                ('declined', False): 'declined',
                                ('declined', 'self'): 'declined',
                                ('declined', 'spouse'): 'declined',
                                ('declined', 'children'): 'declined',
                                ('declined', 'family'): 'declined',
                                })
                        losing = {
                                ('self', 'self'): False,
                                ('self', 'spouse'): False,
                                ('self', 'children'): False,
                                ('self', 'family'): False,
                                ('spouse', 'spouse'): 'self',
                                ('spouse', 'family'): 'children',
                                ('children', 'children'): 'self',
                                ('children', 'family'): 'spouse',
                                }
                        if type == 'medical':
                            losing.update({
                                ('declined', 'declined'): 'self',
                                })
                        present = {
                                ('self', 'family'): True,
                                ('spouse', 'family'): True,
                                ('children', 'family'): True,
                                ('self', 'children'): True,
                                ('spouse', 'children'): False,
                                ('children', 'children'): True,
                                ('self', 'spouse'): True,
                                ('spouse', 'spouse'): True,
                                ('children', 'spouse'): False,
                                ('self', 'self'): True,
                                ('spouse', 'self'): False,
                                ('children', 'self'): False,
                                ('self', False): False,
                                ('spouse', False): False,
                                ('children', False): False,
                                }
                        if type == 'medical':
                            present.update({
                                ('self', 'declined'): False,
                                ('spouse', 'declined'): False,
                                ('children', 'declined'): False,
                                ('declined', 'family'): False,
                                ('declined', 'children'): False,
                                ('declined', 'spouse'): False,
                                ('declined', 'self'): False,
                                ('declined', False): False,
                                ('declined', 'declined'): True,
                                })
                        def fget(self):
                            data = self.__dict__[master]
                            return present[group, data]
                        def fset(self, value):
                            if value not in (True, False):
                                raise ERPError('Logic Error', 'value must be True or False, not %r' % value)
                            if value == present[group, self.__dict__[master]]:
                                # already correct, skip
                                return
                            if value:
                                table = adding
                            else:
                                table = losing
                            data = self.__dict__[master]
                            # print 'setting %r to %r' % (master, table[group, data])
                            self.__dict__[master] = table[group, data]
                        return locals()
                    YearlyRecord[insurance] = nested_property(_generic)
            del type
            del group
            del insurance
            del master
            del _generic
        def coverage(mutable):
            res = mutable['medical'] == mutable['dental'] == mutable['vision'] == mutable['life'] == False
            res = not res
        if not isinstance(ids, (int, long)):
            [ids] = ids
        employee_id = ids
        res = {'value': {}, 'domain': {}, 'warning': {}}
        years = [YearlyRecord(self, cr, uid, employee_id, year, rec) for rec in choice_ids]
        print 'years: %r' % (years, )
        print 'years: %r' % ([y.record for y in years], )
        seen = set()
        dupes = set()
        target = None
        # look for dupes and save target record
        for rec in years:
            group = (seen, dupes)[rec.year in seen]
            group.add(rec.year)
            if rec.year == year:
                # save for later
                target = rec
        if target is None:
            # create record
            target = YearlyRecord(self, cr, uid, employee_id, year, [0, False, {}])
            years.insert(0, target)
        # print 'target: %r' % (target, )
        if dupes:
            res['warning']['title'] = 'Data Error'
            res['warning']['message'] = (
                    'Duplicates years not allowed: %s\n(displaying last record found for year %s)'
                    % (', '.join([str(y) for y in dupes]), year)
                    )
        if type:
            # (un)set value
            attr = '%s_%s' % (type, field)
            # print 'setting %s to %s' % (attr, value)
            setattr(target, attr, value)
            # print 'mutable: %r' % target.mutable
        print 'exploding record'
        # populate detail view with record
        res['value']['hr_insurance_medical_self'] = target.medical_self
        res['value']['hr_insurance_medical_spouse'] = target.medical_spouse
        res['value']['hr_insurance_medical_children'] = target.medical_children
        res['value']['hr_insurance_medical_declined'] = target.medical_declined
        res['value']['hr_insurance_dental_self'] = target.dental_self
        res['value']['hr_insurance_dental_spouse'] = target.dental_spouse
        res['value']['hr_insurance_dental_children'] = target.dental_children
        res['value']['hr_insurance_vision_self'] = target.vision_self
        res['value']['hr_insurance_vision_spouse'] = target.vision_spouse
        res['value']['hr_insurance_vision_children'] = target.vision_children
        res['value']['hr_insurance_life_self'] = target.life_self
        res['value']['hr_insurance_life_spouse'] = target.life_spouse
        res['value']['hr_insurance_life_children'] = target.life_children
        # ween out empty years and update target
        res['value']['hr_insurance_choice_ids'] = [
                y.record for y in years # if y.year == year or coverage(y.mutable)
                ]
        # for k, v in sorted(res['value'].items()):
        #     print '%r: %r' % (k, v)
        print '-' * 50
        return res

class MedicalInsuranceChoice(fields.SelectionEnum):
    self = 'Self'
    spouse = 'w/Spouse'
    children = 'w/Children'
    family = 'w/Family'
    declined = 'Declined'

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

