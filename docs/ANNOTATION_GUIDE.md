# Draft category decision guide

**Draft for review. The frozen version 1 taxonomy and accuracy reports remain unchanged.**

Classify what the bill changes, not everything named in its description. Multiple labels are welcome when multiple substantive provisions support them.

## General decisions

- **Assigned:** enough text supports one or more direct topics. Quote the text and explain the connection.
- **Outside taxonomy:** the subject is clear but none of the ten categories fits. This is not a processing failure.
- **Needs more text:** the description is insufficient to decide. Do not convert this to an empty label set.
- **Pending:** nobody has reviewed the record yet.
- The user selected separate axes: direct policy topics and explicitly affected sectors. Record both independently. A pharmacy tax exemption is taxation plus affected-sector healthcare; healthcare becomes a policy topic only for an additional care/practice provision.
- Never use model similarity or its predicted labels as evidence for a human annotation.

## Topic boundaries

### Housing (`housing`)

Residential housing development, affordability programs, rental relationships, eviction, and homelessness services.

Include: Residential zoning and accessory dwelling units; Rental advertising, tenancy, eviction and residential landlord duties; Housing assistance and homelessness shelter programs.

Exclude: Industrial-only zoning or data-center siting; Real-estate professional licensing without a residential housing provision; A reference to residents or buildings alone.

### Healthcare (`healthcare`)

Medical care, insurance coverage, provider practice, patient rights, and population-health programs.

Include: Mental-health treatment and patient services; Medical-provider practice, licensure and clinical training requirements; Disease prevention and governance of operational public-health programs.

Exclude: A Health Code citation alone; Wages or pensions for healthcare employees without a care/practice provision; A sector-specific tax exemption without a healthcare-service or practice provision.

### Education (`education`)

School and higher-education instruction, educational services, governance, staffing duties, access, and funding.

Include: School curriculum, tuition and teacher duties; Operational duties of schools delivering services; Studies explicitly examining educational participation or outcomes.

Exclude: Student eligibility to work as election officials; School-tax exemptions without a school resource or funding allocation provision; Continuing professional training outside educational institutions.

### Transportation (`transportation`)

Transport networks, mobility, vehicle regulation, driver administration and transport safety.

Include: Road, rail, bus and freight operations; Abandoned or impounded vehicles; Driver/vehicle licensing and transport-administration records.

Exclude: Ceremonial airport or bridge renaming; Housing near transit without a separate transport provision; Generic equipment that happens to be a vehicle.

### Environment (`environment`)

Pollution, waste, conservation, wildlife and environmental protection.

Include: Waste disposal, recycling and illegal dumping; Air/water pollution controls; Wildlife conservation and management.

Exclude: Industrial siting without a stated environmental provision; A Public Resources Code citation alone; A district with a natural-sounding name without environmental duties.

### Energy (`energy`)

Energy generation, distribution, fuels, energy utility services and energy efficiency.

Include: Renewable generation and electricity networks; Building energy efficiency; Energy-service regulation.

Exclude: Water-only district governance; General investment without an energy provision; A reference to an electric appliance alone.

### Taxation (`taxation`)

Tax rates, bases, credits, exemptions, assessment and tax administration.

Include: Creates or repeals a tax credit or exemption; Express property-tax assessment provisions; Tax powers of local districts.

Exclude: Debt administration, bonds, appropriations or fees without tax changes; A statement that tax provisions are unchanged; Assuming an appraisal is a tax assessment without enough context.

### Public safety and justice (`public_safety`)

Criminal justice, criminal procedure, policing, corrections, firearms and emergency response.

Include: Juvenile criminal records and appointed criminal counsel; Grand-jury evidence, forensic case review and sentencing; Operational policing and emergency-response duties.

Exclude: Civil eviction, civil liability or civil court procedure alone; Police officer pensions without policing provisions; Employment background-check acceptance without a criminal-process or public-safety provision; Unspecified jury or investigator procedures when criminal/civil scope is unknown.

### Labor and employment (`labor`)

Employment conditions, worker rights, wages, pensions, hiring access and workforce development.

Include: Severance, paid leave, wages and occupational pension terms; Hiring eligibility and employer screening obligations; Workforce development and labor administration.

Exclude: Public-official ethics or conflicts of interest alone; Business/professional licensing alone; A person described as an employee without an employment provision.

### Elections and voting (`elections`)

Voting access, election administration, electoral districts, candidate eligibility and campaign finance.

Include: Redistricting and electoral boundaries; Election staffing and voting procedures; Changes to board candidate eligibility or selection by voters.

Exclude: An ordinary referendum condition for an unrelated local government action, without a distinct electoral administration change; Appointment of an official without a change to electoral rules; The word candidate used outside elections.

## Examples that require a consistent rule

| Description | Direct topics under this draft | Context / limitation |
|---|---|---|
| Students may serve as poll workers | elections | Students are eligible participants; educational services do not change. |
| Tax exemption for pharmacies | taxation | Healthcare is the affected sector unless the bill separately changes care or practice. |
| Mental-health treatment and school staffing duties | healthcare, education | Both service delivery and school operations change. |
| Officer pension eligibility | labor | Officer occupation alone does not change policing. |
| Rental eviction deadlines | housing | Civil procedure alone is not criminal justice. |
| Data-center zoning | outside taxonomy | Industrial zoning is not residential housing. |
| Community protection program repeal | needs more text | A program name is insufficient evidence. |

This draft is an explicit convention, not a universal truth. Changes to these conventions require a new policy version. Version 1 and version 2 scores are not directly comparable because their label definitions differ.


## Affected sectors

Sector IDs are healthcare, education, housing, transportation, energy, finance, technology, agriculture, government, and commerce. Sector tags identify explicitly targeted domains, not every indirect consequence. Require supporting excerpts just as for policy topics. A sector can share its name with a policy topic, but it is stored separately and never unioned into `topics` for evaluation.

In the review command, an empty sector answer means reviewed with no sector tags. `?` means sector tags were not reviewed; they stay null. For policy topics, use `more` if evidence is insufficient and `outside` only when the subject is clear but outside the ten categories.
