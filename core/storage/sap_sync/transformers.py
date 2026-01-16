from typing import Dict, Any
import json
from datetime import datetime
from core.storage.sap_sync.db_queries import parse_sap_date, calculate_record_hash
from utility.observability.logger import get_logger

logger = get_logger("transformers")


class SAPTransformer:

    @staticmethod
    def transform_sales_order(sap_record: Dict[str, Any]) -> Dict[str, Any]:

        try:
            transformed = {
                # Primary key
                "sales_order": sap_record.get("SalesOrder"),
                # Organization
                "sales_order_type": sap_record.get("SalesOrderType"),
                "sales_organization": sap_record.get("SalesOrganization"),
                "distribution_channel": sap_record.get("DistributionChannel"),
                "organization_division": sap_record.get("OrganizationDivision"),
                "sales_group": sap_record.get("SalesGroup"),
                "sales_office": sap_record.get("SalesOffice"),
                "sales_district": sap_record.get("SalesDistrict"),
                # Customer
                "sold_to_party": sap_record.get("SoldToParty"),
                # Dates
                "creation_date": parse_sap_date(sap_record.get("CreationDate")),
                "last_change_date": parse_sap_date(sap_record.get("LastChangeDate")),
                "sales_order_date": parse_sap_date(sap_record.get("SalesOrderDate")),
                "customer_purchase_order_date": parse_sap_date(
                    sap_record.get("CustomerPurchaseOrderDate")
                ),
                "pricing_date": parse_sap_date(sap_record.get("PricingDate")),
                "requested_delivery_date": parse_sap_date(
                    sap_record.get("RequestedDeliveryDate")
                ),
                "fixed_value_date": parse_sap_date(sap_record.get("FixedValueDate")),
                "billing_document_date": parse_sap_date(
                    sap_record.get("BillingDocumentDate")
                ),
                "services_rendered_date": parse_sap_date(
                    sap_record.get("ServicesRenderedDate")
                ),
                "last_change_date_time": parse_sap_date(
                    sap_record.get("LastChangeDateTime")
                ),
                "external_doc_last_change_date_time": parse_sap_date(
                    sap_record.get("ExternalDocLastChangeDateTime")
                ),
                # User/System
                "created_by_user": sap_record.get("CreatedByUser"),
                "sender_business_system_name": sap_record.get(
                    "SenderBusinessSystemName"
                ),
                # Documents
                "external_document_id": sap_record.get("ExternalDocumentID"),
                "purchase_order_by_customer": sap_record.get("PurchaseOrderByCustomer"),
                "purchase_order_by_ship_to_party": sap_record.get(
                    "PurchaseOrderByShipToParty"
                ),
                "customer_purchase_order_type": sap_record.get(
                    "CustomerPurchaseOrderType"
                ),
                "customer_purchase_order_suplmnt": sap_record.get(
                    "CustomerPurchaseOrderSuplmnt"
                ),
                # Financial
                "total_net_amount": SAPTransformer._parse_decimal(
                    sap_record.get("TotalNetAmount")
                ),
                "transaction_currency": sap_record.get("TransactionCurrency"),
                "price_detn_exchange_rate": SAPTransformer._parse_decimal(
                    sap_record.get("PriceDetnExchangeRate")
                ),
                "accounting_exchange_rate": SAPTransformer._parse_decimal(
                    sap_record.get("AccountingExchangeRate")
                ),
                # Status
                "overall_delivery_status": sap_record.get("OverallDeliveryStatus"),
                "total_block_status": sap_record.get("TotalBlockStatus"),
                "overall_ord_reltd_billg_status": sap_record.get(
                    "OverallOrdReltdBillgStatus"
                ),
                "overall_sd_doc_reference_status": sap_record.get(
                    "OverallSDDocReferenceStatus"
                ),
                "overall_sd_process_status": sap_record.get("OverallSDProcessStatus"),
                "total_credit_check_status": sap_record.get("TotalCreditCheckStatus"),
                "overall_total_delivery_status": sap_record.get(
                    "OverallTotalDeliveryStatus"
                ),
                "overall_sd_document_rejection_sts": sap_record.get(
                    "OverallSDDocumentRejectionSts"
                ),
                "sales_doc_approval_status": sap_record.get("SalesDocApprovalStatus"),
                # Delivery/Shipping
                "shipping_condition": sap_record.get("ShippingCondition"),
                "complete_delivery_is_defined": sap_record.get(
                    "CompleteDeliveryIsDefined", False
                ),
                "shipping_type": sap_record.get("ShippingType"),
                "header_billing_block_reason": sap_record.get(
                    "HeaderBillingBlockReason"
                ),
                "delivery_block_reason": sap_record.get("DeliveryBlockReason"),
                "delivery_date_type_rule": sap_record.get("DeliveryDateTypeRule"),
                # Incoterms
                "incoterms_classification": sap_record.get("IncotermsClassification"),
                "incoterms_transfer_location": sap_record.get(
                    "IncotermsTransferLocation"
                ),
                "incoterms_location1": sap_record.get("IncotermsLocation1"),
                "incoterms_location2": sap_record.get("IncotermsLocation2"),
                "incoterms_version": sap_record.get("IncotermsVersion"),
                # Pricing/Payment
                "customer_price_group": sap_record.get("CustomerPriceGroup"),
                "price_list_type": sap_record.get("PriceListType"),
                "customer_payment_terms": sap_record.get("CustomerPaymentTerms"),
                "payment_method": sap_record.get("PaymentMethod"),
                # Billing
                "billing_plan": sap_record.get("BillingPlan"),
                # References
                "assignment_reference": sap_record.get("AssignmentReference"),
                "reference_sd_document": sap_record.get("ReferenceSDDocument"),
                "reference_sd_document_category": sap_record.get(
                    "ReferenceSDDocumentCategory"
                ),
                "accounting_doc_external_reference": sap_record.get(
                    "AccountingDocExternalReference"
                ),
                "corresp_nc_external_reference": sap_record.get(
                    "CorrespncExternalReference"
                ),
                "po_corresp_nc_external_reference": sap_record.get(
                    "POCorrespncExternalReference"
                ),
                # Customer groups
                "customer_account_assignment_group": sap_record.get(
                    "CustomerAccountAssignmentGroup"
                ),
                "customer_condition_group1": sap_record.get("CustomerConditionGroup1"),
                "customer_condition_group2": sap_record.get("CustomerConditionGroup2"),
                "customer_condition_group3": sap_record.get("CustomerConditionGroup3"),
                "customer_condition_group4": sap_record.get("CustomerConditionGroup4"),
                "customer_condition_group5": sap_record.get("CustomerConditionGroup5"),
                "customer_group": sap_record.get("CustomerGroup"),
                "additional_customer_group1": sap_record.get(
                    "AdditionalCustomerGroup1"
                ),
                "additional_customer_group2": sap_record.get(
                    "AdditionalCustomerGroup2"
                ),
                "additional_customer_group3": sap_record.get(
                    "AdditionalCustomerGroup3"
                ),
                "additional_customer_group4": sap_record.get(
                    "AdditionalCustomerGroup4"
                ),
                "additional_customer_group5": sap_record.get(
                    "AdditionalCustomerGroup5"
                ),
                # Tax
                "customer_tax_classification1": sap_record.get(
                    "CustomerTaxClassification1"
                ),
                "customer_tax_classification2": sap_record.get(
                    "CustomerTaxClassification2"
                ),
                "customer_tax_classification3": sap_record.get(
                    "CustomerTaxClassification3"
                ),
                "customer_tax_classification4": sap_record.get(
                    "CustomerTaxClassification4"
                ),
                "customer_tax_classification5": sap_record.get(
                    "CustomerTaxClassification5"
                ),
                "customer_tax_classification6": sap_record.get(
                    "CustomerTaxClassification6"
                ),
                "customer_tax_classification7": sap_record.get(
                    "CustomerTaxClassification7"
                ),
                "customer_tax_classification8": sap_record.get(
                    "CustomerTaxClassification8"
                ),
                "customer_tax_classification9": sap_record.get(
                    "CustomerTaxClassification9"
                ),
                "tax_departure_country": sap_record.get("TaxDepartureCountry"),
                "vat_registration_country": sap_record.get("VATRegistrationCountry"),
                # Document control
                "sd_document_reason": sap_record.get("SDDocumentReason"),
                "sales_order_approval_reason": sap_record.get(
                    "SalesOrderApprovalReason"
                ),
                "sls_doc_is_rlvt_for_proof_of_deliv": sap_record.get(
                    "SlsDocIsRlvtForProofOfDeliv", False
                ),
                # Additional
                "contract_account": sap_record.get("ContractAccount"),
                "additional_value_days": sap_record.get("AdditionalValueDays"),
                # Metadata
                "record_hash": calculate_record_hash(sap_record),
                "raw_sap_data": json.dumps(sap_record),
            }

            return transformed

        except Exception as e:
            logger.error(
                "transformation_failed",
                sales_order=sap_record.get("SalesOrder"),
                error=str(e),
            )
            raise

    @staticmethod
    def _parse_decimal(value: Any) -> float:

        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
