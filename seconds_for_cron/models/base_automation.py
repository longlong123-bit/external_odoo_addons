# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.tools import ustr
from odoo.addons.base_automation.models.base_automation import (
    DATE_RANGE_FUNCTION,
    DATE_RANGE_FACTOR,
    TIME_TRIGGERS
)

DATE_RANGE_FUNCTION['seconds'] = lambda interval: relativedelta(seconds=interval)

DATE_RANGE_FACTOR.update({
    'seconds': 1,
    'minutes': 60,
    'hour': 60 * 60,
    'day': 24 * 60 * 60,
    'month': 30 * 24 * 60 * 60,
    False: 0,
})


_logger = logging.getLogger(__name__)


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    trg_date_range_type = fields.Selection(selection_add=[('seconds', 'Seconds')], ondelete={'seconds': 'cascade'})

    # Override by Long Duong Nhat
    def _get_cron_interval(self, automations=None):
        """ Return the expected time interval used by the cron, in seconds. """
        def get_delay(rec):
            return rec.trg_date_range * DATE_RANGE_FACTOR[rec.trg_date_range_type]

        if automations is None:
            automations = self.with_context(active_test=True).search([('trigger', 'in', TIME_TRIGGERS)])

        # Minimum 30 seconds, maximum 14400 seconds <=> 4 hours
        delay = min(automations.mapped(get_delay), default=0)
        return min(max(30, delay), 4 * 60 * 60) if delay else 4 * 60 * 60

    # Override by Long Duong Nhat
    def _update_cron(self):
        """ Activate the cron job depending on whether there exists automation rules
        based on time conditions. Also update its frequency according to
        the smallest automation delay, or restore the default 4 hours if there
        is no time based automation.
        """
        cron = self.env.ref('base_automation.ir_cron_data_base_automation_check', raise_if_not_found=False)
        if cron:
            automations = self.with_context(active_test=True).search([('trigger', 'in', TIME_TRIGGERS)])
            cron.try_write({
                'active': bool(automations),
                'interval_type': 'seconds',
                'interval_number': self._get_cron_interval(automations),
            })
