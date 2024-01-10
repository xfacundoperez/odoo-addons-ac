odoo.define('bm.official.action_button', function (require) {
    "use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.find('.oe_action_button').click(this.proxy('action_def'));
            }
        },
        action_def: function () {
            console.log(this.initialState);
            var user = this.initialState.context.uid;
            //var cids = this.initialState.context.params.cids;
            var cids = [];
            $("div[data-menu='company']").each(function (index, div) {
                cids.push(parseInt($(div).attr('data-company-id')))
            })
            var month = parseInt(this.$buttons.find('.oe_action_select_month').val())
            rpc.query({
                model: 'bm.official',
                method: 'js_action_def',
                args: [[user], { cids, month }],
            }).then(function (e) {
                window.location.reload();
            });
        },
    })
})
