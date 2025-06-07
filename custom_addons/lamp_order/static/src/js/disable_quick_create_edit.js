odoo.define('oms_base.disable_many2one_quick_create_edit', function (require) {
    "use strict";

    let relationalFields = require('web.relational_fields');
    relationalFields.FieldMany2One.include({
        init: function (parent, name, record, options) {
            options = options || {};
            this._super.apply(this, arguments);
            this.can_create = false;
            this.can_write = false;
            this.nodeOptions = _.defaults(this.nodeOptions, {
                quick_create: true,
            });
        }
    })
})
