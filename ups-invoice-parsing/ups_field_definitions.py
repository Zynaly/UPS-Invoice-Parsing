"""
Enhanced UPS Field Definitions and Matrix Structure
Based on actual UPS invoice formats and sample data analysis
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class UPSFieldDefinition:
    """Enhanced definition for UPS fields with improved extraction patterns"""
    field_name: str
    display_name: str
    patterns: List[str]
    data_type: str  # 'string', 'float', 'integer', 'date', 'currency', 'currency_triple'
    category: str
    required: bool = False
    validation_regex: str = None
    format_function: callable = None
    priority: int = 1  # 1=highest priority for extraction

class UPSFieldMatrix:
    """Enhanced UPS field matrix based on real invoice analysis"""
    
    def __init__(self):
        self.field_definitions = self._initialize_enhanced_field_definitions()
        self.compiled_patterns = self._compile_patterns()
        self.category_order = self._define_category_order()
    
    def _initialize_enhanced_field_definitions(self) -> Dict[str, UPSFieldDefinition]:
        """Initialize field definitions based on actual UPS invoice formats"""
        
        definitions = {}
        
        # === CORE INVOICE HEADER FIELDS ===
        definitions['invoice_number'] = UPSFieldDefinition(
            field_name='invoice_number',
            display_name='Invoice Number',
            patterns=[
                r'Invoice\s+Number\s+([0-9A-Z]{10,})',
                r'Invoice\s+Date.*?Invoice\s+Number\s+([0-9A-Z]{10,})',
                r'Delivery\s+Service\s+Invoice.*?([0-9A-Z]{10,})',
                r'([0-9A-Z]{10,})\s*(?=.*Account\s+Number)'
            ],
            data_type='string',
            category='Invoice Header',
            required=True,
            priority=1
        )
        
        definitions['account_number'] = UPSFieldDefinition(
            field_name='account_number',
            display_name='Account Number',
            patterns=[
                r'Account\s+Number\s*([A-Z0-9]{4,})',
                r'AccountNumber\s*([A-Z0-9]{4,})',
                r'Account\s*([A-Z0-9]{4,})(?=\s|$)'
            ],
            data_type='string',
            category='Invoice Header',
            required=True,
            priority=1
        )
        
        definitions['control_id'] = UPSFieldDefinition(
            field_name='control_id',
            display_name='Control ID',
            patterns=[
                r'Control\s+ID\s+([A-Z0-9\-#]{2,})',
                r'Control\s*ID\s*:\s*([A-Z0-9\-#]{2,})'
            ],
            data_type='string',
            category='Invoice Header',
            priority=2
        )
        
        definitions['invoice_date'] = UPSFieldDefinition(
            field_name='invoice_date',
            display_name='Invoice Date',
            patterns=[
                r'Invoice\s+Date\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})',
                r'Invoice\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})'
            ],
            data_type='date',
            category='Invoice Header',
            priority=1
        )
        
        definitions['shipped_from'] = UPSFieldDefinition(
            field_name='shipped_from',
            display_name='Shipped From',
            patterns=[
                r'Shipped\s+from:\s*([^\n]+)',
                r'Ship\s+From:\s*([^\n]+)'
            ],
            data_type='string',
            category='Invoice Header',
            priority=2
        )
        
        # === CRITICAL SHIPMENT IDENTIFICATION ===
        definitions['tracking_number'] = UPSFieldDefinition(
            field_name='tracking_number',
            display_name='Tracking Number',
            patterns=[r'(1Z[A-Z0-9]{16})'],
            data_type='string',
            category='Shipment Core',
            required=True,
            validation_regex=r'^1Z[A-Z0-9]{16}$',
            priority=1
        )
        
        definitions['pickup_date'] = UPSFieldDefinition(
            field_name='pickup_date',
            display_name='Pickup Date',
            patterns=[
                r'(\d{2}/\d{2}(?:/\d{2,4})?)',
                r'Pickup\s+Date:?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
            ],
            data_type='date',
            category='Shipment Core',
            required=True,
            priority=1
        )
        
        definitions['shipment_date'] = UPSFieldDefinition(
            field_name='shipment_date',
            display_name='Shipment Date',
            patterns=[
                r'(\d{2}/\d{2}(?:/\d{2,4})?)',
                r'Ship\s+Date:?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
            ],
            data_type='date',
            category='Shipment Core',
            required=True,
            priority=1
        )
        
        # === SERVICE INFORMATION ===
        definitions['service_type'] = UPSFieldDefinition(
            field_name='service_type',
            display_name='Service Type',
            patterns=[
                # Specific UPS service patterns
                r'(UPS\s+Next\s+Day\s+Air\s+Early\s*(?:A\.?M\.?)?)',
                r'(UPS\s+Next\s+Day\s+Air\s+Saver)',
                r'(Next\s+Day\s+Air\s+Residential)',
                r'(UPS\s+Next\s+Day\s+Air)',
                r'(Next\s+Day\s+Air)',
                r'(UPS\s+2nd\s+Day\s+Air\s+A\.?M\.?)',
                r'(2nd\s+Day\s+Air\s+Residential)',
                r'(UPS\s+2nd\s+Day\s+Air)',
                r'(2nd\s+Day\s+Air)',
                r'(UPS\s+3\s+Day\s+Select)',
                r'(3\s+Day\s+Select)',
                r'(UPS\s+Ground\s+Residential)',
                r'(Ground\s+Residential)',
                r'(UPS\s+Ground\s+Commercial)',
                r'(Ground\s+Commercial)',
                r'(UPS\s+Ground)',
                r'(Ground)',
                r'(UPS\s+Standard)',
                r'(Standard)',
                r'(UPS\s+Express\s+Plus)',
                r'(UPS\s+Express)',
                r'(Express)',
                r'(UPS\s+Expedited)',
                r'(Expedited)',
                r'(UPS\s+Saver)',
                r'(Saver)'
            ],
            data_type='string',
            category='Service Info',
            priority=1
        )
        
        # === GEOGRAPHIC DATA ===
        definitions['destination_zip'] = UPSFieldDefinition(
            field_name='destination_zip',
            display_name='Destination ZIP',
            patterns=[
                r'(?:Zip|ZIP|Code)?\s*(\d{5}(?:-\d{4})?)',
                r'(\d{5}(?:-\d{4})?)'
            ],
            data_type='string',
            category='Geographic',
            validation_regex=r'^\d{5}(-\d{4})?$',
            priority=1
        )
        
        definitions['origin_zip'] = UPSFieldDefinition(
            field_name='origin_zip',
            display_name='Origin ZIP',
            patterns=[
                r'Origin\s*ZIP:?\s*(\d{5}(?:-\d{4})?)',
                r'From\s*ZIP:?\s*(\d{5}(?:-\d{4})?)'
            ],
            data_type='string',
            category='Geographic',
            priority=2
        )
        
        definitions['zone'] = UPSFieldDefinition(
            field_name='zone',
            display_name='Zone',
            patterns=[
                r'Zone\s*(\d{1,3})',
                r'\b(\d{1,3})\s+(?=\d+(?:\.\d+)?\s+[\d,]+\.\d{2})',  # Zone before weight and charges
                r'(?:Zone|Zn)\s*(\d{1,3})'
            ],
            data_type='integer',
            category='Geographic',
            priority=1
        )
        
        # === WEIGHT AND DIMENSIONS ===
        definitions['weight'] = UPSFieldDefinition(
            field_name='weight',
            display_name='Weight',
            patterns=[
                r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|LB|LBS)?\s+(?=[\d,]+\.\d{2})',
                r'Weight:?\s*(\d+(?:\.\d+)?)',
                r'(\d+(?:\.\d+)?)\s+(?=[\d,]+\.\d{2}\s*-?[\d,]+\.\d{2})'  # Weight before charges
            ],
            data_type='float',
            category='Weight/Dimensions',
            priority=1
        )
        
        definitions['customer_weight'] = UPSFieldDefinition(
            field_name='customer_weight',
            display_name='Customer Weight',
            patterns=[
                r'Customer\s+Weight\s+(\d+(?:\.\d+)?)',
                r'Cust\s*Wt:?\s*(\d+(?:\.\d+)?)',
                r'Customer\s+Wt:?\s*(\d+(?:\.\d+)?)'
            ],
            data_type='float',
            category='Weight/Dimensions',
            priority=2
        )
        
        definitions['billable_weight'] = UPSFieldDefinition(
            field_name='billable_weight',
            display_name='Billable Weight',
            patterns=[
                r'Billable\s+Weight:?\s*(\d+(?:\.\d+)?)',
                r'Bill\s*Wt:?\s*(\d+(?:\.\d+)?)'
            ],
            data_type='float',
            category='Weight/Dimensions',
            priority=2
        )
        
        definitions['dimensional_weight'] = UPSFieldDefinition(
            field_name='dimensional_weight',
            display_name='Dimensional Weight',
            patterns=[
                r'Dimensional\s+Weight:?\s*(\d+(?:\.\d+)?)',
                r'Dim\s*Wt:?\s*(\d+(?:\.\d+)?)',
                r'DIM\s+Weight:?\s*(\d+(?:\.\d+)?)'
            ],
            data_type='float',
            category='Weight/Dimensions',
            priority=2
        )
        
        definitions['dimensions'] = UPSFieldDefinition(
            field_name='dimensions',
            display_name='Package Dimensions',
            patterns=[
                r'Customer\s+Entered\s+Dimensions\s*=\s*([^\n]+)',
                r'Dimensions\s*=\s*([^\n]+)',
                r'(\d+\s*x\s*\d+\s*x\s*\d+\s*in)',
                r'(\d+\s*x\s*\d+\s*x\s*\d+)'
            ],
            data_type='string',
            category='Weight/Dimensions',
            priority=2
        )
        
        # === BASE CHARGES (CRITICAL FOR ACCURACY) ===
        definitions['published_charge'] = UPSFieldDefinition(
            field_name='published_charge',
            display_name='Published Charge',
            patterns=[
                r'([\d,]+\.\d{2})(?=\s*-?[\d,]+\.\d{2}\s+[\d,]+\.\d{2})',  # First in triple
                r'Published:?\s*([\d,]+\.\d{2})',
                r'Pub:?\s*([\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Base Charges',
            priority=1
        )
        
        definitions['incentive_credit'] = UPSFieldDefinition(
            field_name='incentive_credit',
            display_name='Incentive Credit',
            patterns=[
                r'[\d,]+\.\d{2}\s*(-[\d,]+\.\d{2})\s+[\d,]+\.\d{2}',  # Middle in triple
                r'Incentive:?\s*(-?[\d,]+\.\d{2})',
                r'Inc:?\s*(-?[\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Base Charges',
            priority=1
        )
        
        definitions['billed_charge'] = UPSFieldDefinition(
            field_name='billed_charge',
            display_name='Billed Charge',
            patterns=[
                r'[\d,]+\.\d{2}\s*-?[\d,]+\.\d{2}\s+([\d,]+\.\d{2})(?:\s|$)',  # Last in triple
                r'Billed:?\s*([\d,]+\.\d{2})',
                r'Bill:?\s*([\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Base Charges',
            priority=1
        )
        
        definitions['net_charge'] = UPSFieldDefinition(
            field_name='net_charge',
            display_name='Net Charge',
            patterns=[
                r'Net:?\s*([\d,]+\.\d{2})',
                r'Net\s+Charge:?\s*([\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Base Charges',
            priority=2
        )
        
        # === SURCHARGES (ENHANCED WITH THREE-VALUE PATTERNS) ===
        definitions['residential_surcharge'] = UPSFieldDefinition(
            field_name='residential_surcharge',
            display_name='Residential Surcharge',
            patterns=[
                r'Residential\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'Residential\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'Res\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            data_type='currency_triple',
            category='Surcharges',
            priority=1
        )
        
        definitions['fuel_surcharge'] = UPSFieldDefinition(
            field_name='fuel_surcharge',
            display_name='Fuel Surcharge',
            patterns=[
                r'Fuel\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            data_type='currency_triple',
            category='Surcharges',
            priority=1
        )
        
        definitions['delivery_area_surcharge'] = UPSFieldDefinition(
            field_name='delivery_area_surcharge',
            display_name='Delivery Area Surcharge',
            patterns=[
                r'Delivery\s+Area\s+Surcharge(?:\s*-\s*(?:Extended|Remote))?\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'(?:Extended|Remote)\s+Area\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'DAS\s*-\s*(?:Extended|Remote)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            data_type='currency_triple',
            category='Surcharges',
            priority=1
        )
        
        # Add more surcharges...
        surcharge_types = [
            ('large_package_surcharge', 'Large Package Surcharge', r'Large\s+Package\s+Surcharge'),
            ('additional_handling', 'Additional Handling', r'Additional\s+Handling'),
            ('saturday_delivery', 'Saturday Delivery', r'Saturday\s+Delivery'),
            ('saturday_pickup', 'Saturday Pickup', r'Saturday\s+Pickup'),
            ('signature_required', 'Signature Required', r'Signature\s+(?:Required|Option)'),
            ('adult_signature_required', 'Adult Signature Required', r'Adult\s+Signature\s+Required'),
            ('direct_signature_required', 'Direct Signature Required', r'Direct\s+Signature\s+Required'),
            ('address_correction', 'Address Correction', r'Address\s+Correction(?:\s+Fee)?'),
            ('over_maximum_limits', 'Over Maximum Limits', r'Over\s+Maximum\s+Limits'),
            ('peak_surcharge', 'Peak Surcharge', r'Peak\s+(?:Season\s+)?Surcharge'),
            ('holiday_surcharge', 'Holiday Surcharge', r'Holiday\s+Surcharge'),
            ('hazmat_surcharge', 'Hazmat Surcharge', r'(?:Hazmat|Hazardous\s+Materials?)\s*(?:Fee|Surcharge)'),
            ('dry_ice_surcharge', 'Dry Ice Surcharge', r'Dry\s+Ice\s*(?:Fee|Surcharge)'),
            ('declared_value_charge', 'Declared Value Charge', r'Declared\s+Value\s*(?:Charge|Fee)'),
            ('cod_surcharge', 'COD Surcharge', r'(?:COD|Cash\s+on\s+Delivery)\s*(?:Fee|Surcharge)'),
            ('carbon_neutral', 'Carbon Neutral', r'Carbon\s+Neutral'),
            ('lift_gate_surcharge', 'Lift Gate Surcharge', r'Lift\s+Gate\s*(?:Fee|Surcharge)'),
            ('inside_pickup', 'Inside Pickup', r'Inside\s+Pickup'),
            ('inside_delivery', 'Inside Delivery', r'Inside\s+Delivery'),
            ('call_tag_surcharge', 'Call Tag Surcharge', r'Call\s+Tag\s*(?:Fee|Surcharge)'),
            ('quantum_view', 'Quantum View', r'Quantum\s+View\s*(?:Notify|Manage)?'),
            ('ups_premium_care', 'UPS Premium Care', r'UPS\s+Premium\s+Care'),
            ('missing_pld_fee', 'Missing PLD Fee', r'Missing\s+PLD\s+Fee')
        ]
        
        for field_name, display_name, base_pattern in surcharge_types:
            definitions[field_name] = UPSFieldDefinition(
                field_name=field_name,
                display_name=display_name,
                patterns=[
                    f'{base_pattern}\\s+([\\d,]+\\.\\d{{2}})\\s*(-?[\\d,]+\\.\\d{{2}})\\s+([\\d,]+\\.\\d{{2}})'
                ],
                data_type='currency_triple',
                category='Surcharges',
                priority=2
            )
        
        # === REFERENCE FIELDS ===
        definitions['first_reference'] = UPSFieldDefinition(
            field_name='first_reference',
            display_name='1st Reference',
            patterns=[
                r'1st\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*1:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*1:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='References',
            priority=2
        )
        
        definitions['second_reference'] = UPSFieldDefinition(
            field_name='second_reference',
            display_name='2nd Reference',
            patterns=[
                r'2nd\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*2:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*2:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='References',
            priority=2
        )
        
        definitions['third_reference'] = UPSFieldDefinition(
            field_name='third_reference',
            display_name='3rd Reference',
            patterns=[
                r'3rd\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*3:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*3:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='References',
            priority=2
        )
        
        definitions['user_id'] = UPSFieldDefinition(
            field_name='user_id',
            display_name='User ID',
            patterns=[
                r'UserID:?\s*([A-Za-z0-9\-_]+)',
                r'User\s*ID:?\s*([A-Za-z0-9\-_]+)',
                r'UID:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='References',
            priority=2
        )
        
        definitions['purchase_order'] = UPSFieldDefinition(
            field_name='purchase_order',
            display_name='Purchase Order',
            patterns=[
                r'(?:Purchase\s+Order|PO|P\.O\.)\s*:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='References',
            priority=2
        )
        
        # === ADDRESS INFORMATION ===
        definitions['sender_name'] = UPSFieldDefinition(
            field_name='sender_name',
            display_name='Sender Name',
            patterns=[
                r'Sender\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*Receiver|\n|$)',
                r'Ship\s*From\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*Ship\s*To|\n|$)',
                r'From\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*To|\n|$)'
            ],
            data_type='string',
            category='Address Info',
            priority=2
        )
        
        definitions['sender_address'] = UPSFieldDefinition(
            field_name='sender_address',
            display_name='Sender Address',
            patterns=[
                r'Sender\s*:?\s*[A-Z][A-Za-z\s&\.,\-\']+?\s+([0-9][^\n]*)',
                r'Ship\s*From\s*:?\s*[A-Z][A-Za-z\s&\.,\-\']+?\s+([0-9][^\n]*)'
            ],
            data_type='string',
            category='Address Info',
            priority=2
        )
        
        definitions['receiver_name'] = UPSFieldDefinition(
            field_name='receiver_name',
            display_name='Receiver Name',
            patterns=[
                r'Receiver\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*\d|\n|Message|$)',
                r'Ship\s*To\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*\d|\n|$)',
                r'Consignee\s*:?\s*([A-Z][A-Za-z\s&\.,\-\']+?)(?=\s*\d|\n|$)'
            ],
            data_type='string',
            category='Address Info',
            priority=2
        )
        
        definitions['receiver_address'] = UPSFieldDefinition(
            field_name='receiver_address',
            display_name='Receiver Address',
            patterns=[
                r'Receiver\s*:?\s*[A-Z][A-Za-z\s&\.,\-\']+?\s+([0-9][^\n]*)',
                r'Ship\s*To\s*:?\s*[A-Z][A-Za-z\s&\.,\-\']+?\s+([0-9][^\n]*)'
            ],
            data_type='string',
            category='Address Info',
            priority=2
        )
        
        # === SERVICE OPTIONS ===
        definitions['cod_amount'] = UPSFieldDefinition(
            field_name='cod_amount',
            display_name='COD Amount',
            patterns=[
                r'COD\s*Amount:?\s*([\d,]+\.\d{2})',
                r'Cash\s+on\s+Delivery:?\s*([\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Service Options',
            priority=2
        )
        
        definitions['declared_value'] = UPSFieldDefinition(
            field_name='declared_value',
            display_name='Declared Value',
            patterns=[
                r'Declared\s+Value:?\s*([\d,]+\.\d{2})'
            ],
            data_type='currency',
            category='Service Options',
            priority=2
        )
        
        # === TIME INFORMATION ===
        definitions['delivery_date'] = UPSFieldDefinition(
            field_name='delivery_date',
            display_name='Delivery Date',
            patterns=[
                r'Delivery\s+Date:?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                r'Delivered:?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
            ],
            data_type='date',
            category='Time Info',
            priority=2
        )
        
        definitions['commit_time'] = UPSFieldDefinition(
            field_name='commit_time',
            display_name='Commit Time',
            patterns=[
                r'Commit\s+Time:?\s*(\d{1,2}:\d{2}(?:\s*[AP]M)?)',
                r'By:?\s*(\d{1,2}:\d{2}(?:\s*[AP]M)?)'
            ],
            data_type='string',
            category='Time Info',
            priority=2
        )
        
        # === PACKAGE INFORMATION ===
        definitions['package_type'] = UPSFieldDefinition(
            field_name='package_type',
            display_name='Package Type',
            patterns=[
                r'Package\s+Type:?\s*([^\n]+)',
                r'Packaging:?\s*([^\n]+)'
            ],
            data_type='string',
            category='Package Info',
            priority=2
        )
        
        definitions['number_of_packages'] = UPSFieldDefinition(
            field_name='number_of_packages',
            display_name='Number of Packages',
            patterns=[
                r'(\d+)\s*(?:Package|Pkg|Piece)s?',
                r'Qty:?\s*(\d+)',
                r'Count:?\s*(\d+)'
            ],
            data_type='integer',
            category='Package Info',
            priority=2
        )
        
        # === ADDITIONAL INFORMATION ===
        definitions['message_codes'] = UPSFieldDefinition(
            field_name='message_codes',
            display_name='Message Codes',
            patterns=[
                r'Message\s+Codes?:?\s*([a-z0-9\s,]+)',
                r'Msg\s+Code:?\s*([a-z0-9\s,]+)',
                r'Code:?\s*([a-z0-9\s,]+)(?=\s*$|\n)'
            ],
            data_type='string',
            category='Additional Info',
            priority=2
        )
        
        # === TOTALS (CRITICAL FOR VALIDATION) ===
        definitions['line_total'] = UPSFieldDefinition(
            field_name='line_total',
            display_name='Line Total',
            patterns=[
                r'Total\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'Line\s+Total\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            data_type='currency_triple',
            category='Line Totals',
            priority=1
        )
        
        # === ACCOUNT FIELDS ===
        definitions['shipper_account'] = UPSFieldDefinition(
            field_name='shipper_account',
            display_name='Shipper Account',
            patterns=[
                r'Shipper\s+Account:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='Account Info',
            priority=2
        )
        
        definitions['third_party_account'] = UPSFieldDefinition(
            field_name='third_party_account',
            display_name='Third Party Account',
            patterns=[
                r'Third\s+Party\s+Account:?\s*([A-Za-z0-9\-_]+)',
                r'3rd\s+Party:?\s*([A-Za-z0-9\-_]+)'
            ],
            data_type='string',
            category='Account Info',
            priority=2
        )
        
        return definitions
    
    def _compile_patterns(self) -> Dict[str, List]:
        """Compile all regex patterns for efficient matching"""
        compiled = {}
        for field_name, definition in self.field_definitions.items():
            compiled[field_name] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                for pattern in definition.patterns
            ]
        return compiled
    
    def _define_category_order(self) -> List[str]:
        """Define the order of categories for Excel output"""
        return [
            'Invoice Header',
            'Shipment Core',
            'Service Info',
            'Geographic',
            'Weight/Dimensions',
            'Base Charges',
            'Surcharges',
            'Line Totals',
            'References',
            'Address Info',
            'Service Options',
            'Time Info',
            'Package Info',
            'Account Info',
            'Additional Info'
        ]
    
    def get_fields_by_category(self) -> Dict[str, List[str]]:
        """Get fields organized by category in priority order"""
        categories = {}
        for field_name, definition in self.field_definitions.items():
            category = definition.category
            if category not in categories:
                categories[category] = []
            categories[category].append((field_name, definition.priority))
        
        # Sort by priority within each category
        for category in categories:
            categories[category].sort(key=lambda x: x[1])  # Sort by priority
            categories[category] = [field_name for field_name, priority in categories[category]]
        
        # Return in defined order
        ordered_categories = {}
        for category in self.category_order:
            if category in categories:
                ordered_categories[category] = categories[category]
        
        return ordered_categories
    
    def get_excel_column_order(self) -> List[str]:
        """Get the optimal column order for Excel output matching sample format"""
        
        # Start with control columns
        columns = [
            'ROW_TYPE', 'SHIPMENT_INDEX', 'SHIPMENT_COUNT', 'TOTAL_SHIPMENTS'
        ]
        
        # Add high-priority fields first
        high_priority_fields = [
            'invoice_number', 'tracking_number', 'account_number', 'invoice_date',
            'destination_zip', 'page_number', 'invoice_group', 'processing_type',
            'weight', 'zone', 'service_type', 'published_charge', 'incentive_credit'
        ]
        
        columns.extend(high_priority_fields)
        
        # Add surcharges in specific order
        surcharge_fields = [
            'fuel_surcharge', 'fuel_surcharge_published', 'fuel_surcharge_incentive', 'fuel_surcharge_billed',
            'dimensions', 'receiver_name', 'customer_weight',
            'residential_surcharge', 'residential_surcharge_published', 'residential_surcharge_incentive', 'residential_surcharge_billed',
            'shipment_date', 'billed_charge', 'message_codes',
            'delivery_area_surcharge', 'delivery_area_surcharge_published', 'delivery_area_surcharge_incentive', 'delivery_area_surcharge_billed'
        ]
        
        columns.extend(surcharge_fields)
        
        # Add remaining fields by category
        categories = self.get_fields_by_category()
        for category, fields in categories.items():
            for field in fields:
                if field not in columns:
                    columns.append(field)
                    # Add surcharge sub-fields
                    if self.field_definitions[field].data_type == 'currency_triple':
                        sub_fields = [f"{field}_published", f"{field}_incentive", f"{field}_billed"]
                        for sub_field in sub_fields:
                            if sub_field not in columns:
                                columns.append(sub_field)
        
        return columns
    
    def validate_field_value(self, field_name: str, value: Any) -> Tuple[bool, str]:
        """Validate a field value according to its definition"""
        if field_name not in self.field_definitions:
            return False, f"Unknown field: {field_name}"
        
        definition = self.field_definitions[field_name]
        
        if value is None and not definition.required:
            return True, ""
        
        if value is None and definition.required:
            return False, f"Required field {field_name} is missing"
        
        # Type-specific validation
        if definition.data_type == 'integer':
            try:
                int(str(value).replace(',', ''))
            except ValueError:
                return False, f"Field {field_name} must be an integer"
        
        elif definition.data_type == 'float':
            try:
                float(str(value).replace(',', ''))
            except ValueError:
                return False, f"Field {field_name} must be a number"
        
        elif definition.data_type == 'currency':
            try:
                float(str(value).replace(',', '').replace('', ''))
            except ValueError:
                return False, f"Field {field_name} must be a currency value"
        
        # Regex validation
        if definition.validation_regex:
            if not re.match(definition.validation_regex, str(value)):
                return False, f"Field {field_name} format is invalid"
        
        return True, ""
    
    def get_high_priority_fields(self) -> List[str]:
        """Get list of high-priority fields for extraction"""
        high_priority = []
        for field_name, definition in self.field_definitions.items():
            if definition.priority == 1:
                high_priority.append(field_name)
        return high_priority
