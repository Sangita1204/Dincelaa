# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class tax_report_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		if not data:
			company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
			data = {
				'form': {
					'based_on': 'invoices',
					'company_id': company_id,
					'display_detail': False,
				}
			}
		self.period_ids = []
		period_obj = self.pool.get('account.period')
		self.display_detail = data['form']['display_detail']
		self.date_from = data['form']['date_from']
		self.date_to = data['form']['date_to']
		_logger.error("set_contextset_context-0[" + str(self.date_from)+"][" +str(self.date_to)+"]")
		res['periods'] = ''
		res['fiscalyear'] = data['form'].get('fiscalyear_id', False)

		if data['form'].get('period_from', False) and data['form'].get('period_to', False):
			self.period_ids = period_obj.build_ctx_periods(self.cr, self.uid, data['form']['period_from'], data['form']['period_to'])
			periods_l = period_obj.read(self.cr, self.uid, self.period_ids, ['name'])
			for period in periods_l:
				if res['periods'] == '':
					res['periods'] = period['name']
				else:
					res['periods'] += ", "+ period['name']
		return super(tax_report_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(tax_report_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update({
			'time': time,
			'get_codes': self._get_codes_dcs,
			'get_general': self._get_general,
			'get_currency': self._get_currency,
			'get_lines': partial(self._get_lines_dcs, context=context),
			'get_fiscalyear': self._get_fiscalyear,
			'get_account': self._get_account,
			'get_start_period': self.get_start_period,
			'get_end_period': self.get_end_period,
			'get_start_date': self._get_start_date,
			'get_end_date': self._get_end_date,
			'get_basedon': self._get_basedon,
		})
	def _get_start_date(self, form):
		return form['form']['date_from']
	def _get_end_date(self, form):
		return form['form']['date_to']
		
	def _get_basedon(self, form):
		return form['form']['based_on']

	def _get_lines_dcs(self, based_on, company_id=False, parent=False, level=0, context=None):
		period_list = self.period_ids
		#_logger.error("_get_general_period_listperiod_list-"+str(period_list))
		res = self._get_codes_dcs(based_on, company_id, parent, level, period_list, context=context)
		  
		'''if period_list:
			res = self._add_codes_dcs(based_on, res, period_list, context=context)
		else:
			self.cr.execute ("select id from account_fiscalyear")
			fy = self.cr.fetchall()
			self.cr.execute ("select id from account_period where fiscalyear_id = %s",(fy[0][0],))
			periods = self.cr.fetchall()
			for p in periods:
				period_list.append(p[0])
			res = self._add_codes_dcs(based_on, res, period_list, context=context)
		'''
		i = 0
		top_result = []
		while i < len(res):
			res_dict = { 'code': res[i][1]['code'],
				'name': res[i][1]['name'],
				'date_invoice': '--',
				'partner_name': '--',
				'number': '--',
				'purchase_amt':self._get_sum_tax(res[i][1]['id'], company_id, "purchase", context=context),
				'purchase_tax':self._get_sum_tax(res[i][1]['id'], company_id, "purchasetax", context=context),
				'sale_amt':self._get_sum_tax(res[i][1]['id'], company_id, "sale", context=context),
				'sale_tax':self._get_sum_tax(res[i][1]['id'], company_id, "saletax", context=context),
				'debit': 0,
				'credit': 0,
				'tax_amount': res[i][1]['sum_period'],
				'type': 1,
				'level': res[i][0],
				'pos': 0
			}

			top_result.append(res_dict)
			res_general = self._get_general(res[i][1]['id'], period_list, company_id, based_on, context=context)
			ind_general = 0
			while ind_general < len(res_general):
				res_general[ind_general]['type']  = 2
				res_general[ind_general]['pos']   = 0
				res_general[ind_general]['level'] = res_dict['level']
				top_result.append(res_general[ind_general])
				ind_general+=1
			i+=1
		return top_result
	
	def _get_sum_tax(self, tax_code_id, company_id, _type,  context=None):
		 
		res = []
		sql = None 
		if _type=="sale":  
			sql ="select t.type, \
				 case when t.type in('sale','out_invoice') then sum(t.base_amount) \
					  when t.type in('out_refund') then sum(-1*t.base_amount) \
					  else 0 end as tot_amt"
		elif _type=="saletax":  
			sql ="select t.type, \
				 case when t.type in('sale','out_invoice') then sum(t.tax_amount) \
					  when t.type in('out_refund') then sum(-1*t.tax_amount) \
					  else 0 end as tot_amt"
		elif _type=="purchase":  
			sql ="select t.type, \
				 case when t.type in('purchase','in_invoice') then sum(t.base_amount) \
					  when t.type in('in_refund') then sum(-1*t.base_amount) \
					  else 0 end as tot_amt"
		elif _type=="purchasetax":  
			sql ="select t.type, \
				 case when t.type in('purchase','in_invoice') then sum(t.tax_amount) \
					  when t.type in('in_refund') then sum(-1*t.tax_amount) \
					  else 0 end as tot_amt"
		else:
			return 0
		'''sql="select t.id,t.number,t.date_invoice,t.partner_name,t.tax_amount,'-' AS name,t.tax_code as code, \
			case when t.type in('purchase','in_invoice') then t.base_amount \
				 when t.type in('in_refund') then -1*t.base_amount \
				 else 0 end as purchase_amt, \
			case when t.type in('sale','out_invoice') then t.base_amount \
				 when t.type in('out_refund') then -1*t.base_amount \
				 else 0 end as sale_amt, \
			case when t.type in('purchase','in_invoice') then t.tax_amount \
				 when t.type in('in_refund') then -1*t.tax_amount \
				 else 0 end as purchase_tax, \
			case when t.type in('sale','out_invoice') then t.tax_amount \
				 when t.type in('out_refund') then -1*t.tax_amount \
				 else 0 end  as sale_tax \
			from dincelaccount_tax as t \
			where t.tax_code_id=%s \
				 and t.company_id = %s \
				 and (t.date_invoice between %s and %s)"'''
		
		#_logger.error("_get_general_get_general-nonpayments["+str(sql)+"]")	
		if sql:
			sql += " from dincelaccount_tax as t \
					where t.tax_code_id=%s \
					 and t.company_id = %s \
					 and (t.date_invoice between %s and %s) group by t.type"
			self.cr.execute(sql,(tax_code_id, company_id, self.date_from, self.date_to,))
			res = self.cr.dictfetchall()
			amt=0
			for data in res:	
				amt += data['tot_amt']
			return amt
		else:
			return 0
		
	def _get_general(self, tax_code_id, period_list, company_id, based_on, context=None):
		if not self.display_detail:
			return []
		res = []
		obj_account = self.pool.get('account.account')
		periods_ids = tuple(period_list)
		  
		sql="select t.id,t.number,t.date_invoice,t.partner_name,t.tax_amount,'.' AS name,'.' as code, \
			case when t.type in('purchase','in_invoice') then t.base_amount \
				 when t.type in('in_refund') then -1*t.base_amount \
				 else 0 end as purchase_amt, \
			case when t.type in('sale','out_invoice') then t.base_amount \
				 when t.type in('out_refund') then -1*t.base_amount \
				 else 0 end as sale_amt, \
			case when t.type in('purchase','in_invoice') then t.tax_amount \
				 when t.type in('in_refund') then -1*t.tax_amount \
				 else 0 end as purchase_tax, \
			case when t.type in('sale','out_invoice') then t.tax_amount \
				 when t.type in('out_refund') then -1*t.tax_amount \
				 else 0 end  as sale_tax \
			from dincelaccount_tax as t \
			where t.tax_code_id=%s \
				 and t.company_id = %s \
				 and (t.date_invoice between %s and %s) \
			order by t.date_invoice "
		
		#_logger.error("_get_general_get_general-nonpayments["+str(sql)+"]")		
		self.cr.execute(sql,(tax_code_id, company_id, self.date_from, self.date_to,))
		res = self.cr.dictfetchall()
		return res

	def _get_codes_dcs(self, based_on, company_id, parent=False, level=0, period_list=None, context=None):
		obj_tc = self.pool.get('account.tax.code')
		ids = obj_tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)], context=context)

		res = []
		for code in obj_tc.browse(self.cr, self.uid, ids, {'based_on': based_on}):
			res.append(('.'*2*level, code))

			res += self._get_codes_dcs(based_on, company_id, code.id, level+1, context=context)
		return res

	def _add_codes_dcs(self, based_on, account_list=None, period_list=None, context=None):
		if context is None:
			context = {}

		if account_list is None:
			account_list = []
		if period_list is None:
			period_list = []
		res = []
		obj_tc = self.pool.get('account.tax.code')
		for account in account_list:
			ids = obj_tc.search(self.cr, self.uid, [('id','=', account[1].id)], context=context)
			code = {}
			for period_ind in period_list:
				context2 = dict(context, period_id=period_ind, based_on=based_on)
				record = obj_tc.browse(self.cr, self.uid, ids, context=context2)[0]
				if not code:
					code = {
						'id': record.id,
						'name': record.name,
						'code': record.code,
						'sequence': record.sequence,
						'sum_period': 0,
						'sale_tax': 0,
					}
				code['sale_tax'] +=1.1#;record.sum_period

			res.append((account[0], code))
		return res

	def _get_currency(self, form, context=None):
		return self.pool.get('res.company').browse(self.cr, self.uid, form['company_id'], context=context).currency_id.name

	def sort_result(self, accounts, context=None):
		# On boucle sur notre rapport
		result_accounts = []
		ind=0
		old_level=0
		while ind<len(accounts):
			#
			account_elem = accounts[ind]
			#

			#
			# we will now check if the level is lower than the previous level, in this case we will make a subtotal
			if (account_elem['level'] < old_level):
				bcl_current_level = old_level
				bcl_rup_ind = ind - 1

				while (bcl_current_level >= int(accounts[bcl_rup_ind]['level']) and bcl_rup_ind >= 0 ):
					res_tot = { 'code': accounts[bcl_rup_ind]['code'],
						'name': '',
						'date_invoice':  accounts[bcl_rup_ind]['date_invoice'],
						'debit': 0,
						'credit': 0,
						'tax_amount': accounts[bcl_rup_ind]['tax_amount'],
						'type': accounts[bcl_rup_ind]['type'],
						'level': 0,
						'pos': 0
					}

					if res_tot['type'] == 1:
						# on change le type pour afficher le total
						res_tot['type'] = 2
						result_accounts.append(res_tot)
					bcl_current_level =  accounts[bcl_rup_ind]['level']
					bcl_rup_ind -= 1

			old_level = account_elem['level']
			result_accounts.append(account_elem)
			ind+=1

		return result_accounts


class report_tax_dcs(osv.AbstractModel):
	_name = 'report.account.report_tax_dcs'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_tax_dcs'
	_wrapped_report_class = tax_report_dcs

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
