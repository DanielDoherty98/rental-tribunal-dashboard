"""
Synthetic decision documents used by the tests and the sample builder.

REAL_CASE_0690 and REAL_CASE_1300 reproduce the two failures reported against
V5.1. They are permanent regression tests - if either regresses, the suite
fails before any scrape can run.
"""

# ------------------------------------------------------------------ reported failures
# Reported: determined rent not found at all. The figure sits in the boxes
# beside numbered item 1 on the pre-RRA form.
REAL_CASE_0690 = """
FIRST-TIER TRIBUNAL PROPERTY CHAMBER (RESIDENTIAL PROPERTY)

Case Reference:   MAN/00BU/MNR/2025/0690
Property:   4 Example Street, Manchester M14 5TG
Landlord:   Northern Homes Limited
Tenant:   Ms K Ahmed

Date of application:   12 May 2025
Date of decision:   28 July 2025

Rent currently payable:   £950.00 per calendar month
Rent proposed by the landlord:   £1250.00 per calendar month

DECISION

1.   The rent is   £1175   per calendar month

with effect from 1 August 2025.

2.   The sum of £250 is payable in respect of fees.
"""

# Reported: read as £130 instead of £1300 - the money regex truncation.
REAL_CASE_1300 = """
FIRST-TIER TRIBUNAL PROPERTY CHAMBER (RESIDENTIAL PROPERTY)

Case Reference:   LON/00AH/MNR/2025/0412
Property:   Flat 3, 22 Example Gardens, London SE15 4TP
Landlord:   Southside Property Group Limited
Tenant:   Mr R Whitfield

Date of application:   3 March 2025
Date of decision:   19 May 2025

Rent currently payable:   £1100.00 per calendar month
Rent proposed by the landlord:   £1400.00 per calendar month

DECISION

1.   The rent is   £1300   per calendar month

with effect from 1 June 2025.
"""

# Same form, table flattened one cell per line by the PDF extractor.
CELL_PER_LINE = """
Case Reference:   LEE/00DA/MNR/2025/0155
Property:   9 Sample Avenue, Leeds LS6 2AA
Date of decision:   4 June 2025
Rent currently payable:   £800.00 per calendar month
Rent proposed by the landlord:   £1100.00 per calendar month

DECISION
1.
The rent is
£1025
per calendar month
"""

POST_RRA = """
FIRST-TIER TRIBUNAL PROPERTY CHAMBER (RESIDENTIAL PROPERTY)
DECISION AND REASONS

Case Reference: LON/00AY/MNR/2026/0155
Property: Flat 10 Langley Mansions, Langley Lane, London SW8 1TJ
Landlord: Grainger Residential Management Limited
Landlord's representative: Ms J Patel of Grainger Residential Management Limited
Tenant: Mr A Okonkwo
Date of the section 13 notice: 3 April 2026
Date of application: 24 May 2026
Date of hearing: 12 June 2026
Date of decision: 19 June 2026

Rent currently payable: £780.00 per month
Rent proposed by the landlord: £1050.00 per month
Effective date: 1 July 2026

The tenant's case
The tenant did not provide any comparable evidence. The tenant proposed £914.07 per month.
The tenant submitted photographs showing damp and mould in the bathroom and said no
supporting evidence of market rents was available to him.

The landlord's case
The landlord relied on four comparables: 12 Wandsworth Road, 8 Nine Elms Lane,
44 Kennington Road and 6 Albert Embankment. The landlord provided letting agent
particulars and Rightmove listing evidence in support of £1050.00 per month.

The Tribunal's decision and reasons
The Tribunal considered the comparable evidence provided by the landlord and made a
deduction to reflect the condition of the bathroom and the absence of white goods.
Having regard to the open market rent for similar properties in the locality, the
Tribunal determines a rent of £985.00 per month with effect from 1 July 2026.
"""

PRE_RRA_ONE_PAGE = """
RESIDENTIAL PROPERTY TRIBUNAL SERVICE
NOTICE OF DECISION

Address of premises
21 Kingsley Street, Birkenhead, Wirral CH41 0BQ

Case number MAN/00BY/MNR/2019/0044

Landlord Riverside Housing Association Limited
Tenant Mrs S Grant

Date of notice of increase 14 January 2019
Date of application 2 February 2019

The rent for the above property is

£675

per calendar month with effect from 1 March 2019

Chairman: Mr P Reynolds
Dated 26 February 2019
"""

WEEKLY_CASE = """
Case Reference: BIR/00CN/MNR/2023/0099
Property: 5 Alcester Road, Birmingham B13 8AT
Landlord: Mr D Shah
Date of application: 10 March 2023
Date of decision: 4 May 2023
Rent currently payable: £150.00 per week
Rent proposed by the landlord: £185.00 per week
The Tribunal determines a rent of £172.00 per week with effect from 1 June 2023.
The landlord submitted no comparables and did not attend the hearing.
"""

WITHDRAWN_CASE = """
Case Reference: CHI/00HN/MNR/2024/0210
Property: 14 Sea View Terrace, Brighton BN2 3PL
Landlord: Coastal Lettings Ltd
Date of application: 8 August 2024
Date of decision: 19 September 2024
Rent currently payable: £1100.00 per calendar month
Rent proposed by the landlord: £1300.00 per calendar month
The application is withdrawn by the tenant before the hearing and the Tribunal
therefore makes no determination of the rent.
"""
