/** @odoo-module **/
    import FormController from 'web.FormController';
    import { session } from "@web/session";

    let all_readonly_model = ['sale.order', 'stock.picking'];
    let stock_model = ['stock.picking'];
    let sale_readonly_status = ['sale', 'done', 'cancel', 'sent'];
    let stock_readonly_status = 'done';

    FormController.include({
        updateButtons: function(){

            let self = this;
            let res = this._super.apply(this, arguments);

            let isUserAdmin = false

            let mode_name = this.modelName;
            all_readonly_model.forEach(function (value) {
                // 销售订单
                if (value === mode_name && sale_readonly_status.includes(self.renderer.state.data.state) && !isUserAdmin) {
                    if (self.$buttons !== undefined) {
                        self.$buttons.find('.o_form_button_edit').hide();
                    }
                    self.mode = 'readonly';
                } else if (value === mode_name && !sale_readonly_status.includes(self.renderer.state.data.state) && !isUserAdmin) {
                    if (self.$buttons !== undefined) {
                        self.$buttons.find('.o_form_button_edit').show();
                    }
                }
            });
            stock_model.find(function(value){
                if(value === mode_name && self.renderer.state.data.state === stock_readonly_status && !isUserAdmin){
                    if(self.$buttons !== undefined){
                        self.$buttons.find('.o_form_button_edit').hide();
                    }
                    self.mode === 'readonly'
                }else if(value === mode_name && self.renderer.state.data.state != stock_readonly_status && !isUserAdmin){
                    if(self.$buttons !== undefined){
                        self.$buttons.find('.o_form_button_edit').show();
                    }
                }
            })

            return res;
        }
    });
