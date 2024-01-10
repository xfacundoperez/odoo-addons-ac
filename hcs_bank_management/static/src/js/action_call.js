/*
odoo.define('bm.official.action_button', function (require) {
    "use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;
    // Seteo el año
    var _year = new Date().getFullYear()
    var _month = new Date().getMonth() + 1
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                // Set Month
                this.$buttons.find('#oe_action_select_month')
                    .val(_month);
                // Set Year
                this.$buttons.find('#oe_action_input_year')
                    .attr('max', _year)
                    .val(_year)
                    .change(this.proxy('change_year'));
                // Action button
                if (this.$buttons) {
                    this.$buttons.find('.oe_action_button').click(this.proxy('action_def'));
                }
            }
        },
        action_def: function () {
            var user = this.initialState.context.uid;
            //var cids = this.initialState.context.params.cids;
            var cids = [];
            $("div[data-menu='company']").each(function (index, div) {
                cids.push(parseInt($(div).attr('data-company-id')))
            })
            var month = parseInt(this.$buttons.find('#oe_action_select_month').val())
            var year = parseInt(this.$buttons.find('#oe_action_input_year').val())
            rpc.query({
                model: 'bm.official',
                method: 'js_action_def',
                args: [[user], { cids, month, year }],
            }).then(function (e) {
                window.location.reload();
            });
        },
        change_year: function (input) {
            // Max cur year
            if (input.target.value > _year)
                input.target.value = _year;
            // Min min year
            if (input.target.value < parseInt(input.target.min))
                input.target.value = parseInt(input.target.min);
            // Remove decimal
            input.target.value = ~~input.target.value;

        }
    })
})
 */