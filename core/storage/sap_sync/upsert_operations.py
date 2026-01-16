from typing import Dict, Any, Tuple
from utility.observability.logger import get_logger

logger = get_logger("upsert_operations")


class UpsertOperations:

    @staticmethod
    def upsert_record(cursor, pg_record: Dict[str, Any]) -> str:

        sales_order = pg_record["sales_order"]
        new_hash = pg_record["record_hash"]

        # Check if exists
        cursor.execute(
            "SELECT record_hash FROM sales_orders WHERE sales_order = %s",
            (sales_order,),
        )

        existing = cursor.fetchone()

        if existing is None:
            UpsertOperations._insert(cursor, pg_record)
            return "inserted"

        elif existing[0] != new_hash:
            UpsertOperations._update(cursor, pg_record)
            return "updated"

        else:
            return "unchanged"

    @staticmethod
    def _insert(cursor, record: Dict[str, Any]):

        cursor.execute(
            """
            INSERT INTO sales_orders (
                sales_order, sales_order_type, sales_organization,
                distribution_channel, organization_division, sales_group,
                sales_office, sales_district, sold_to_party,
                creation_date, last_change_date, sales_order_date,
                customer_purchase_order_date, pricing_date, requested_delivery_date,
                fixed_value_date, billing_document_date, services_rendered_date,
                last_change_date_time, external_doc_last_change_date_time,
                created_by_user, sender_business_system_name, external_document_id,
                purchase_order_by_customer, purchase_order_by_ship_to_party,
                customer_purchase_order_type, customer_purchase_order_suplmnt,
                total_net_amount, transaction_currency, price_detn_exchange_rate,
                accounting_exchange_rate, overall_delivery_status, total_block_status,
                overall_ord_reltd_billg_status, overall_sd_doc_reference_status,
                overall_sd_process_status, total_credit_check_status,
                overall_total_delivery_status, overall_sd_document_rejection_sts,
                sales_doc_approval_status, shipping_condition, complete_delivery_is_defined,
                shipping_type, header_billing_block_reason, delivery_block_reason,
                delivery_date_type_rule, incoterms_classification, incoterms_transfer_location,
                incoterms_location1, incoterms_location2, incoterms_version,
                customer_price_group, price_list_type, customer_payment_terms,
                payment_method, billing_plan, assignment_reference,
                reference_sd_document, reference_sd_document_category,
                accounting_doc_external_reference, corresp_nc_external_reference,
                po_corresp_nc_external_reference, customer_account_assignment_group,
                customer_condition_group1, customer_condition_group2,
                customer_condition_group3, customer_condition_group4,
                customer_condition_group5, customer_group, additional_customer_group1,
                additional_customer_group2, additional_customer_group3,
                additional_customer_group4, additional_customer_group5,
                customer_tax_classification1, customer_tax_classification2,
                customer_tax_classification3, customer_tax_classification4,
                customer_tax_classification5, customer_tax_classification6,
                customer_tax_classification7, customer_tax_classification8,
                customer_tax_classification9, tax_departure_country,
                vat_registration_country, sd_document_reason,
                sales_order_approval_reason, sls_doc_is_rlvt_for_proof_of_deliv,
                contract_account, additional_value_days, record_hash, raw_sap_data
            ) VALUES (
                %(sales_order)s, %(sales_order_type)s, %(sales_organization)s,
                %(distribution_channel)s, %(organization_division)s, %(sales_group)s,
                %(sales_office)s, %(sales_district)s, %(sold_to_party)s,
                %(creation_date)s, %(last_change_date)s, %(sales_order_date)s,
                %(customer_purchase_order_date)s, %(pricing_date)s, %(requested_delivery_date)s,
                %(fixed_value_date)s, %(billing_document_date)s, %(services_rendered_date)s,
                %(last_change_date_time)s, %(external_doc_last_change_date_time)s,
                %(created_by_user)s, %(sender_business_system_name)s, %(external_document_id)s,
                %(purchase_order_by_customer)s, %(purchase_order_by_ship_to_party)s,
                %(customer_purchase_order_type)s, %(customer_purchase_order_suplmnt)s,
                %(total_net_amount)s, %(transaction_currency)s, %(price_detn_exchange_rate)s,
                %(accounting_exchange_rate)s, %(overall_delivery_status)s, %(total_block_status)s,
                %(overall_ord_reltd_billg_status)s, %(overall_sd_doc_reference_status)s,
                %(overall_sd_process_status)s, %(total_credit_check_status)s,
                %(overall_total_delivery_status)s, %(overall_sd_document_rejection_sts)s,
                %(sales_doc_approval_status)s, %(shipping_condition)s, %(complete_delivery_is_defined)s,
                %(shipping_type)s, %(header_billing_block_reason)s, %(delivery_block_reason)s,
                %(delivery_date_type_rule)s, %(incoterms_classification)s, %(incoterms_transfer_location)s,
                %(incoterms_location1)s, %(incoterms_location2)s, %(incoterms_version)s,
                %(customer_price_group)s, %(price_list_type)s, %(customer_payment_terms)s,
                %(payment_method)s, %(billing_plan)s, %(assignment_reference)s,
                %(reference_sd_document)s, %(reference_sd_document_category)s,
                %(accounting_doc_external_reference)s, %(corresp_nc_external_reference)s,
                %(po_corresp_nc_external_reference)s, %(customer_account_assignment_group)s,
                %(customer_condition_group1)s, %(customer_condition_group2)s,
                %(customer_condition_group3)s, %(customer_condition_group4)s,
                %(customer_condition_group5)s, %(customer_group)s, %(additional_customer_group1)s,
                %(additional_customer_group2)s, %(additional_customer_group3)s,
                %(additional_customer_group4)s, %(additional_customer_group5)s,
                %(customer_tax_classification1)s, %(customer_tax_classification2)s,
                %(customer_tax_classification3)s, %(customer_tax_classification4)s,
                %(customer_tax_classification5)s, %(customer_tax_classification6)s,
                %(customer_tax_classification7)s, %(customer_tax_classification8)s,
                %(customer_tax_classification9)s, %(tax_departure_country)s,
                %(vat_registration_country)s, %(sd_document_reason)s,
                %(sales_order_approval_reason)s, %(sls_doc_is_rlvt_for_proof_of_deliv)s,
                %(contract_account)s, %(additional_value_days)s, %(record_hash)s, %(raw_sap_data)s
            )
        """,
            record,
        )

    @staticmethod
    def _update(cursor, record: Dict[str, Any]):

        cursor.execute(
            """
            UPDATE sales_orders SET
                total_net_amount = %(total_net_amount)s,
                overall_delivery_status = %(overall_delivery_status)s,
                overall_sd_process_status = %(overall_sd_process_status)s,
                record_hash = %(record_hash)s,
                last_updated_at = NOW(),
                raw_sap_data = %(raw_sap_data)s,
                embedding = NULL
            WHERE sales_order = %(sales_order)s
        """,
            record,
        )
