# 📄 Trade Data Mapping Details
## Source Fields, Rules, Target Fields

**Banco Internacional**

# Bank field:
_id
# Example content:
68c33f2f1481963013c3bc06
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
trade_date.fecha
# Example content:
11/09/2025
# Target field:
header.tradeDate.date
# Instructions:
Map to DD/MM/YYYY format (convert if not already in that format, but should be OK)
# Mandatory input field:
Yes

# Bank field:
deal_number
# Example content:
7555
# Target field:
header.tradeId
# Instructions:
Maintain exactly as informed by bank
# Mandatory input field:
Yes

# Bank field:
counterparty.name
# Example content:
MORGAN STANLEY AND CO
# Target field:
header.party2.partyName
# Instructions:
Maintain exactly as informed by bank
# Mandatory input field:
Yes

# Bank field:
counterparty.rut.rut
# Example content:
453906828
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
counterparty.rut.dv
# Example content:
3
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
counterparty.other
# Example content:
ABC
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
portfolio
# Example content:
SWAP
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
hedge_accounting
# Example content:
NO
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
product
# Example content:
SWAP_ICP
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
currency_pair
# Example content:
CLPCLP
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
price
# Example content:
123.45
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
settlement_mechanism
# Example content:
enum: C or E
# Target field:
legs[0].settlementType + legs[1].settlementType
# Instructions:
You need to populate both of the target fields with the same value. The mapping rule is as follows: If the source bank field has a value of "C" then both target fields need a value of "CASH". If the source bank field has a value of "E" then both target fields need a value of "PHYSICAL". 
# Mandatory input field:
Yes

# Bank field:
other.regulatory_portfolio
# Example content:
NEGOCIACION
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.rp
# Example content:
Enum: A or P
# Target field:
legs[0].payerPartyReference
legs[0].receiverPartyReference
or
legs[1].payerPartyReference
legs[1].receiverPartyReference
# Instructions:
This is a key and very important field. It indicates whether this leg (indicated by the index [n]) is the leg that the bank receives (will have a value of A) or pays (will have a value of P). In the target structure, the legs[0] object is ALWAYS the leg that the bank receives (and the counterparty pays), the target legs[0].payerPartyReference value will always be OurCounterparty and legs[0].receiverPartyReference will always be ThisBank. In the same vein, the legs[1] object is ALWAYS the leg that the counterparty receives (and the bank pays), so the target legs[1].payerPartyReference value will always be ThisBank and legs[1].receiverPartyReference will always be OurCounterparty. It is important to consider that the legs[0].leg_generator.rp will not actually populate legs[0].payerPartyReference, legs[0].receiverPartyReference, legs[1].payerPartyReference or legs[1].receiverPartyReference, as these will be hardcoded in the output. It will however, allow the program to determine which leg refers to the paying or receiving leg.
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.rp
# Example content:
Enum: A or P
# Target field:
legs[0].payerPartyReference
legs[0].receiverPartyReference
or
legs[1].payerPartyReference
legs[1].receiverPartyReference
# Instructions:
This is a key and very important field. It indicates whether this leg (indicated by the index [n]) is the leg that the bank receives (will have a value of A) or pays (will have a value of P). In the target structure, the legs[0] object is ALWAYS the leg that the bank receives (and the counterparty pays), the target legs[0].payerPartyReference value will always be OurCounterparty and legs[0].receiverPartyReference will always be ThisBank. In the same vein, the legs[1] object is ALWAYS the leg that the counterparty receives (and the bank pays), so the target legs[1].payerPartyReference value will always be ThisBank and legs[1].receiverPartyReference will always be OurCounterparty. It is important to consider that the legs[0].leg_generator.rp will not actually populate legs[0].payerPartyReference, legs[0].receiverPartyReference, legs[1].payerPartyReference or legs[1].receiverPartyReference, as these will be hardcoded in the output. It will however, allow the program to determine which leg refers to the paying or receiving leg.
# Mandatory input field:
Yes

# Bank field:
legs[0].type_of_leg
# Example content:
Enum: FIXED_RATE_MCCY, OVERNIGHT_INDEX_MCCY, FIXED_RATE (others that I don't know yet)
# Target field:
legs[0].calculationDayConvention or legs[1].calculationDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessDayConvention or legs[1].effectiveDate.businessDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessDayConvention or legs[1].terminationDate.businessDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
FIXED_RATE_MCCY should be translated to FIXED
FIXED_RATE should be translated to FIXED
OVERNIGHT_INDEX_MCCY should be translated to FLOATING
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_number
# Example content:
1
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.start_date.fecha
# Example content:
15/09/2025
# Target field:
legs[0].effectiveDate.date or legs[1].effectiveDate.date (depending on whether this is pay or receive for the bank)
# Instructions:
Map to DD/MM/YYYY format (convert if not already in that format, but should be OK)
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.end_date.fecha
# Example content:
15/09/2025
# Target field:
legs[0].terminationDate.date or legs[1].terminationDate.date (depending on whether this is pay or receive for the bank)
# Instructions:
Map to DD/MM/YYYY format (convert if not already in that format, but should be OK)
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.bus_adj_rule
# Example content:
Enum: MOD_FOLLOW, FOLLOW, DONT_MOVE (others that I don't know yet)
# Target field:
legs[0].calculationDayConvention or legs[1].calculationDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessDayConvention or legs[1].effectiveDate.businessDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessDayConvention or legs[1].terminationDate.businessDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.settlement_calendar
# Example content:
Enum: NY-SCL, NY, SCL, LON, LON-SCL (others that I don't know yet)
# Target field:
legs[0].paymentBusinessCenters or legs[0].paymentBusinessCenters (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessCenters or legs[1].effectiveDate.businessCenters (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessCenters or legs[1].terminationDate.businessCenters (depending on whether this is pay or receive for the bank) AND legs[0].calculationDayConvention.businessCenters or legs[1].calculationDayConvention.businessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
In the target fields, these values are expressed as an array of strings indicating all applicable business centers. Therefore NY should translate as ["USNY"], SCL should translate as ["CLSA"], LON should translate as ["GBLO"]. And those calendars made of two or more should translate as follows: NY-SCL should translate as ["USNY","CLSA"], LON-SCL should translate as ["GBLO","CLSA"], NY-LON-SCL should translate as ["USNY","GBLO","CLSA"], etc.
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.coupon_rate_type
(Sometimes named legs[0].leg_generator.interest_rate, but this should be treated the same as legs[0].leg_generator.coupon_rate_type. Only one of these values is needed in the target file)
# Example content:
Enum: LIN_ACT/360 (others that I don't know yet)
# Target field:
legs[0].dayCountFraction or legs[1].dayCountFraction (depending on whether this is pay or receive for the bank)
# Instructions:
LIN_ACT/360 should be translated to ACT/360
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.notional_or_custom.initial_notional
# Example content:
65200000000
# Target field:
legs[0].notionalAmount or legs[1].notionalAmount (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain numeric value. Use a point (.) as the decimal marker. Remove thousands separators if they are included.
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.notional_currency
# Example content:
Enum: CLP, USD, GBP, EUR (ISO Currency codes)
# Target field:
legs[0].notionalCurrency or legs[1].notionalCurrency (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain as they arrive
# Mandatory input field:
Yes

# Bank field:
legs[0].coupon_rate_value
# Example content:
0.0463
# Target field:
legs[0].fixedRate or legs[1].fixedRate (depending on whether this is pay or receive for the bank)
# Instructions:
Only applies to legs which have legs[n].rateType = FIXED. The equivalent target field on a floating leg would be legs[n].floatingRateIndex
# Mandatory input field:
No

# Bank field:
legs[0].leg_generator.settlement_stub_period
# Example content:
CORTO INICIO
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON (for now, might include in a later iteration)
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.type_of_amortization
# Example content:
BULLET
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON (for now, might include in a later iteration)
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.amort_is_cashflow
# Example content:
TRUE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.is_bond
# Example content:
FALSE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.maturity.agnos
legs[0].leg_generator.maturity.meses
legs[0].leg_generator.maturity.dias
# Example content:
0
9
0
# Target field:
legs[0].calculationPeriodFrequency or legs[1].calculationPeriodFrequency (depending on whether this is pay or receive for the bank)
# Instructions:
This is a complicated set of fields, which is used in conjunction to determine the frequency of the calculationPeriod. If, for example the input values are 0,9,0 for these three fields, the calculationPeriodFrequency would be 9 months, although I'm not yet sure how to express that in the output JSON.
If the period expressed in the input values is longer than the period between legs[0].leg_generator.start_date.fecha and legs[0].leg_generator.end_date.fecha (e.g. 25,0,0) then this indicates a zero coupon leg and therefore the calculationPeriodFrequency would be set as TERM.
# Mandatory input field:
Yes, although 0 is a valid value

# Bank field:
legs[0].leg_generator.settlement_periodicity.agnos
legs[0].leg_generator.settlement_periodicity.meses
legs[0].leg_generator.settlement_periodicity.dias
# Example content:
0
9
0
# Target field:
legs[0].paymentFrequency or legs[1].paymentFrequency (depending on whether this is pay or receive for the bank)
# Instructions:
This is a complicated set of fields, which is used in conjunction to determine the frequency of the paymentFrequency. If, for example the input values are 0,6,0 for these three fields, the paymentFrequency would be 6 months, although I'm not yet sure how to express that in the output JSON.
If the period expressed in the input values is longer than the period between legs[0].leg_generator.start_date.fecha and legs[0].leg_generator.end_date.fecha (e.g. 25,0,0) then this indicates a zero coupon leg and therefore the paymentFrequency would be set as ATMATURITY.
# Mandatory input field:
Yes, although 0 is a valid value

# Bank field:
legs[0].leg_generator.settlement_lag
# Example content:
1
# Target field:
legs[0].paymentDateOffset or legs[1].paymentDateOffset (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain as in the input value
# Mandatory input field:
Yes

# Bank field:
legs[0].leg_generator.sett_lag_behaviour
# Example content:
Enum: DONT_MOVE, FOLLOW, MOD_FOLLOW (others that I don't know yet)
# Target field:
legs[0].paymentDayConvention or legs[1].paymentDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[0].multi_currency.settlement_currency
# Example content:
Enum: CLP, USD, GBP, EUR (ISO Currency codes)
# Target field:
legs[0].settlementCurrency or legs[1].settlementCurrency (depending on whether this is pay or receive for the bank)
# Instructions:
This field may not always be present in the input file. If it is present, maintain the same ISO code as in the input. However, the target field (legs[n].settlementCurrency) MUST always be populated. If the input field is not present, populate the target field with the same value as is present in legs[n].notionalCurrency
# Mandatory input field:
No, not applicable (but it is mandatory in target file)

# Bank field:
legs[0].multi_currency.fx_rate_index_name
# Example content:
Enum: USDOBS (and others that I don't know yet)
# Target field:
legs[0].fxFixing.fxFixingReference or legs[1].fxFixing.fxFixingReference (depending on whether this is pay or receive for the bank)
# Instructions:
USDOBS should be translated to CLP_DOLAR_OBS_CLP10
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[0].multi_currency.fx_fixing_lag
# Example content:
1
# Target field:
legs[0].fxFixing.fxFixingOffset or legs[1].fxFixing.fxFixingOffset AND legs[0].fxFixing.fxFixingDayConvention or legs[1].fxFixing.fxFixingDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].fxFixing.fxFixingBusinessCenters or legs[1].fxFixing.fxFixingBusinessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
Translate legs[n].multi_currency.fx_fixing_lag 1 to -2 in the target file (legs[n].fxFixing.fxFixingOffset). I need to view more examples of this to determine the correct behaviour, but for the time being do this.
Set legs[n].fxFixing.fxFixingDayConvention to PRECEDING in the target file. Set legs[b].fxFixing.fxFixingBusinessCenters to the same calendars as are set in legs[n].calculationBusinessCenters
# Mandatory input field:
No

# Bank field:
legs[0].multi_currency.fx_fixing_lag_pivot
# Example content:
Enum: SETTLEMENT_DATE (I don't know the other values yet)
# Target field:
legs[0].fxFixing.dateRelativeTo or legs[0].fxFixing.dateRelativeTo (depending on whether this is pay or receive for the bank)
# Instructions:
Translate SETTLEMENT_DATE to PAYMENT_DATES
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[0].multi_currency.fx_fixing_lag_applies_to
# Example content:
PUBLISHING_DATE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.overnight_index_name
# Example content:
Enum: ICPCLP (I don't know the other values yet)
# Target field:
legs[0].floatingRateIndex or legs[1].floatingRateIndex (depending on whether this is pay or receive for the bank)
# Instructions:
Translate ICPCLP to CLP-ICP
I don't yet know the other input enums, will complement the list later
Only applies to legs which have legs[n].rateType = FLOATING. The equivalent target field on a fixed leg would be legs[n].coupon_rate_value
# Mandatory input field:
No, only applies to some floating legs

# Bank field:
legs[0].leg_generator.fix_adj_rule
# Example content:
Enum: DONT_MOVE, FOLLOW, MOD_FOLLOW (others that I don't know yet)
# Target field:
legs[0].resetDayConvention or legs[0].resetDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No, only applies to floating legs

# Bank field:
legs[0].leg_generator.fixing_calendar
# Example content:
Enum: NY-SCL, NY, SCL, LON, LON-SCL (others that I don't know yet)
# Target field:
legs[0].resetBusinessCenters or legs[1].resetBusinessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
In the target fields, these values are expressed as an array of strings indicating all applicable business centers. Therefore NY should translate as ["USNY"], SCL should translate as ["CLSA"], LON should translate as ["GBLO"]. And those calendars made of two or more should translate as follows: NY-SCL should translate as ["USNY","CLSA"], LON-SCL should translate as ["GBLO","CLSA"], NY-LON-SCL should translate as ["USNY","GBLO","CLSA"], etc.
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No, only applies to floating legs

# Bank field:
legs[0].leg_generator.eq_rate_decimal_places
# Example content:
6
# Target field:
legs[0].rateRoundingPrecision or legs[1].rateRoundingPrecision (depending on whether this is pay or receive for the bank) AND legs[0].rateRoundingDirection or legs[1].rateRoundingDirection (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain legs[n].rateRoundingPrecision just as in input file. Also set legs[n].rateRoundingDirection to NEAREST
# Mandatory input field:
No, only applies to some floating legs

# Bank field:
legs[0].leg_generator.spread
# Example content:
0
# Target field:
legs[0].spread or legs[1].spread (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain same value as input, to the same number of decimal places
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.gearing
# Example content:
1
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[0].leg_generator.dates_for_eq_rate
# Example content:
ACCRUAL
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

************************

# Bank field:
legs[1].type_of_leg
# Example content:
Enum: FIXED_RATE_MCCY, OVERNIGHT_INDEX_MCCY, FIXED_RATE (others that I don't know yet)
# Target field:
legs[0].calculationDayConvention or legs[1].calculationDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessDayConvention or legs[1].effectiveDate.businessDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessDayConvention or legs[1].terminationDate.businessDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
FIXED_RATE_MCCY should be translated to FIXED
FIXED_RATE should be translated to FIXED
OVERNIGHT_INDEX_MCCY should be translated to FLOATING
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_number
# Example content:
2
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.start_date.fecha
# Example content:
15/09/2025
# Target field:
legs[0].effectiveDate.date or legs[1].effectiveDate.date (depending on whether this is pay or receive for the bank)
# Instructions:
Map to DD/MM/YYYY format (convert if not already in that format, but should be OK)
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.end_date.fecha
# Example content:
15/09/2025
# Target field:
legs[0].terminationDate.date or legs[1].terminationDate.date (depending on whether this is pay or receive for the bank)
# Instructions:
Map to DD/MM/YYYY format (convert if not already in that format, but should be OK)
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.bus_adj_rule
# Example content:
Enum: MOD_FOLLOW, FOLLOW, DONT_MOVE (others that I don't know yet)
# Target field:
legs[0].calculationDayConvention or legs[1].calculationDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessDayConvention or legs[1].effectiveDate.businessDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessDayConvention or legs[1].terminationDate.businessDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.settlement_calendar
# Example content:
Enum: NY-SCL, NY, SCL, LON, LON-SCL (others that I don't know yet)
# Target field:
legs[0].paymentBusinessCenters or legs[0].paymentBusinessCenters (depending on whether this is pay or receive for the bank) AND legs[0].effectiveDate.businessCenters or legs[1].effectiveDate.businessCenters (depending on whether this is pay or receive for the bank) AND legs[0].terminationDate.businessCenters or legs[1].terminationDate.businessCenters (depending on whether this is pay or receive for the bank) AND legs[0].calculationDayConvention.businessCenters or legs[1].calculationDayConvention.businessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
In the target fields, these values are expressed as an array of strings indicating all applicable business centers. Therefore NY should translate as ["USNY"], SCL should translate as ["CLSA"], LON should translate as ["GBLO"]. And those calendars made of two or more should translate as follows: NY-SCL should translate as ["USNY","CLSA"], LON-SCL should translate as ["GBLO","CLSA"], NY-LON-SCL should translate as ["USNY","GBLO","CLSA"], etc.
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.coupon_rate_type
(Sometimes named legs[1].leg_generator.interest_rate, but this should be treated the same as legs[1].leg_generator.coupon_rate_type. Only one of these values is needed in the target file)
# Example content:
Enum: LIN_ACT/360 (others that I don't know yet)
# Target field:
legs[0].dayCountFraction or legs[1].dayCountFraction (depending on whether this is pay or receive for the bank)
# Instructions:
LIN_ACT/360 should be translated to ACT/360
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.notional_or_custom.initial_notional
# Example content:
65200000000
# Target field:
legs[0].notionalAmount or legs[1].notionalAmount (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain numeric value. Use a point (.) as the decimal marker. Remove thousands separators if they are included.
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.notional_currency
# Example content:
Enum: CLP, USD, GBP, EUR (ISO Currency codes)
# Target field:
legs[0].notionalCurrency or legs[1].notionalCurrency (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain as they arrive
# Mandatory input field:
Yes

# Bank field:
legs[1].coupon_rate_value
# Example content:
0.0463
# Target field:
legs[0].fixedRate or legs[1].fixedRate (depending on whether this is pay or receive for the bank)
# Instructions:
Only applies to legs which have legs[n].rateType = FIXED. The equivalent target field on a floating leg would be legs[n].floatingRateIndex
# Mandatory input field:
No

# Bank field:
legs[1].leg_generator.settlement_stub_period
# Example content:
CORTO INICIO
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON (for now, might include in a later iteration)
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.type_of_amortization
# Example content:
BULLET
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON (for now, might include in a later iteration)
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.amort_is_cashflow
# Example content:
TRUE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.is_bond
# Example content:
FALSE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.maturity.agnos
legs[1].leg_generator.maturity.meses
legs[1].leg_generator.maturity.dias
# Example content:
0
9
0
# Target field:
legs[0].calculationPeriodFrequency or legs[1].calculationPeriodFrequency (depending on whether this is pay or receive for the bank)
# Instructions:
This is a complicated set of fields, which is used in conjunction to determine the frequency of the calculationPeriod. If, for example the input values are 0,9,0 for these three fields, the calculationPeriodFrequency would be 9 months, although I'm not yet sure how to express that in the output JSON.
If the period expressed in the input values is longer than the period between legs[1].leg_generator.start_date.fecha and legs[1].leg_generator.end_date.fecha (e.g. 25,0,0) then this indicates a zero coupon leg and therefore the calculationPeriodFrequency would be set as TERM.
# Mandatory input field:
Yes, although 0 is a valid value

# Bank field:
legs[1].leg_generator.settlement_periodicity.agnos
legs[1].leg_generator.settlement_periodicity.meses
legs[1].leg_generator.settlement_periodicity.dias
# Example content:
0
9
0
# Target field:
legs[0].paymentFrequency or legs[1].paymentFrequency (depending on whether this is pay or receive for the bank)
# Instructions:
This is a complicated set of fields, which is used in conjunction to determine the frequency of the paymentFrequency. If, for example the input values are 0,6,0 for these three fields, the paymentFrequency would be 6 months, although I'm not yet sure how to express that in the output JSON.
If the period expressed in the input values is longer than the period between legs[1].leg_generator.start_date.fecha and legs[1].leg_generator.end_date.fecha (e.g. 25,0,0) then this indicates a zero coupon leg and therefore the paymentFrequency would be set as ATMATURITY.
# Mandatory input field:
Yes, although 0 is a valid value

# Bank field:
legs[1].leg_generator.settlement_lag
# Example content:
1
# Target field:
legs[0].paymentDateOffset or legs[1].paymentDateOffset (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain as in the input value
# Mandatory input field:
Yes

# Bank field:
legs[1].leg_generator.sett_lag_behaviour
# Example content:
Enum: DONT_MOVE, FOLLOW, MOD_FOLLOW (others that I don't know yet)
# Target field:
legs[0].paymentDayConvention or legs[1].paymentDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[1].multi_currency.settlement_currency
# Example content:
Enum: CLP, USD, GBP, EUR (ISO Currency codes)
# Target field:
legs[0].settlementCurrency or legs[1].settlementCurrency (depending on whether this is pay or receive for the bank)
# Instructions:
This field may not always be present in the input file. If it is present, maintain the same ISO code as in the input. However, the target field (legs[n].settlementCurrency) MUST always be populated. If the input field is not present, populate the target field with the same value as is present in legs[n].notionalCurrency
# Mandatory input field:
No, not applicable (but it is mandatory in target file)

# Bank field:
legs[1].multi_currency.fx_rate_index_name
# Example content:
Enum: USDOBS (and others that I don't know yet)
# Target field:
legs[0].fxFixing.fxFixingReference or legs[1].fxFixing.fxFixingReference (depending on whether this is pay or receive for the bank)
# Instructions:
USDOBS should be translated to CLP_DOLAR_OBS_CLP10
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[1].multi_currency.fx_fixing_lag
# Example content:
1
# Target field:
legs[0].fxFixing.fxFixingOffset or legs[1].fxFixing.fxFixingOffset AND legs[0].fxFixing.fxFixingDayConvention or legs[1].fxFixing.fxFixingDayConvention (depending on whether this is pay or receive for the bank) AND legs[0].fxFixing.fxFixingBusinessCenters or legs[1].fxFixing.fxFixingBusinessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
Translate legs[n].multi_currency.fx_fixing_lag 1 to -2 in the target file (legs[n].fxFixing.fxFixingOffset). I need to view more examples of this to determine the correct behaviour, but for the time being do this.
Set legs[n].fxFixing.fxFixingDayConvention to PRECEDING in the target file. Set legs[b].fxFixing.fxFixingBusinessCenters to the same calendars as are set in legs[n].calculationBusinessCenters
# Mandatory input field:
No

# Bank field:
legs[1].multi_currency.fx_fixing_lag_pivot
# Example content:
Enum: SETTLEMENT_DATE (I don't know the other values yet)
# Target field:
legs[0].fxFixing.dateRelativeTo or legs[0].fxFixing.dateRelativeTo (depending on whether this is pay or receive for the bank)
# Instructions:
Translate SETTLEMENT_DATE to PAYMENT_DATES
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No

# Bank field:
legs[1].multi_currency.fx_fixing_lag_applies_to
# Example content:
PUBLISHING_DATE
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.overnight_index_name
# Example content:
Enum: ICPCLP (I don't know the other values yet)
# Target field:
legs[0].floatingRateIndex or legs[1].floatingRateIndex (depending on whether this is pay or receive for the bank)
# Instructions:
Translate ICPCLP to CLP-ICP
I don't yet know the other input enums, will complement the list later
Only applies to legs which have legs[n].rateType = FLOATING. The equivalent target field on a fixed leg would be legs[n].coupon_rate_value
# Mandatory input field:
No, only applies to some floating legs

# Bank field:
legs[1].leg_generator.fix_adj_rule
# Example content:
Enum: DONT_MOVE, FOLLOW, MOD_FOLLOW (others that I don't know yet)
# Target field:
legs[0].resetDayConvention or legs[0].resetDayConvention (depending on whether this is pay or receive for the bank)
# Instructions:
MOD_FOLLOW should be translated to MODFOLLOWING
FOLLOW should be translated to FOLLOWING
DONT_MOVE should be translated to NONE
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No, only applies to floating legs

# Bank field:
legs[1].leg_generator.fixing_calendar
# Example content:
Enum: NY-SCL, NY, SCL, LON, LON-SCL (others that I don't know yet)
# Target field:
legs[0].resetBusinessCenters or legs[1].resetBusinessCenters (depending on whether this is pay or receive for the bank)
# Instructions:
In the target fields, these values are expressed as an array of strings indicating all applicable business centers. Therefore NY should translate as ["USNY"], SCL should translate as ["CLSA"], LON should translate as ["GBLO"]. And those calendars made of two or more should translate as follows: NY-SCL should translate as ["USNY","CLSA"], LON-SCL should translate as ["GBLO","CLSA"], NY-LON-SCL should translate as ["USNY","GBLO","CLSA"], etc.
I don't yet know the other input enums, will complement the list later
# Mandatory input field:
No, only applies to floating legs

# Bank field:
legs[1].leg_generator.eq_rate_decimal_places
# Example content:
6
# Target field:
legs[0].rateRoundingPrecision or legs[1].rateRoundingPrecision (depending on whether this is pay or receive for the bank) AND legs[0].rateRoundingDirection or legs[1].rateRoundingDirection (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain legs[n].rateRoundingPrecision just as in input file. Also set legs[n].rateRoundingDirection to NEAREST
# Mandatory input field:
No, only applies to some floating legs

# Bank field:
legs[1].leg_generator.spread
# Example content:
0
# Target field:
legs[0].spread or legs[1].spread (depending on whether this is pay or receive for the bank)
# Instructions:
Maintain same value as input, to the same number of decimal places
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.gearing
# Example content:
1
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable

# Bank field:
legs[1].leg_generator.dates_for_eq_rate
# Example content:
ACCRUAL
# Target field:
N/A
# Instructions:
Ignore, we do not need this in the output JSON
# Mandatory input field:
No, not applicable
