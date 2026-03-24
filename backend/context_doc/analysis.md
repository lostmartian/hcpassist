### Table defs

The csv files are structured with star schema design.

#### Dimension tables (who, where, when) - basically we can filter and group our analysis using these

- Territory_dim
    - Columns: territory_id, name, geo_type, parent_territory_id
    - Purpose:
- hcp_dim (hcp = health care professionals)
    - Columns: hcp_id, full_name, specialty, tier, territory_id
    - Purpose: Linking to territory_dim to find which doc operates in which region
- account_dim
    - Columns: account_id, name, account_type (hospital or clinic), address, territory_id
    - Purpose: Links healthcare facilities to the territory region
- rep_dim
    - Columns: rep_id, first_name, last_name, region
    - Purpose: Sales rep working in the region
    - REGION IS TERRITORY_ID
- date_dim:
    - Columns: date_id, calendar_date (YYYY-MM-DD), year(YYYY), quarter(Q1,2,3,4), week_num, day_of_week(First three letters of day)

#### Fact tables (what, how much)

- fact_rx: Who write how many total/new prescriptions and when
    - Columns: hcp_id, date_id, brand_code, trx_cnt, nrx_cnt
    - *Links:* `hcp_id` (Who wrote it), `date_id` (When)
- fact_rep_activity: tracking sales rep activity
    - Columns: activity_id, rep_id, hcp_id, account_id, date_id, activity_type, status, time_of_day, duration_min
- fact_payor_mix: how the payments at healthcare facilities are made and when and what the type of method contributes to as percentage
    - Columns: account_id, date_id, payor_type, pct_of_volume
- fact_in_metrix: market share and patient count of hcp or health facility
    - Columns: entity_type, entity_id, quarter_id, ln_patient_cnt, est_market_share
    - If entity_type is “H” then its hcp entity_id and if “A” then its account_id

---

### Domain Glossary:
- HCP: Healthcare Professional (a doctor)
- TRx: Total Prescriptions written
- NRx: New Prescriptions written
- Tier: HCP importance level (A=highest, B=mid, C=lowest)
- GAZYVA: The pharmaceutical brand being tracked
- Payor Mix: Distribution of payment types at a facility
- Metro Area / State Cluster: Types of geographic territories
- Entity Type H: HCP-level metric, Entity Type A: Account-level metric

---

#### Did some data analysis on notebook: https://colab.research.google.com/drive/1QSuA9WBLYfnVLDac7VLIwPtZFlqSpbLX?usp=sharing

---

Found these insights:

TEMPORAL GUARDRAILS
Data Window: 2024-08-01 to 2025-12-31

ALLOWED (ENUMS)
hcp_dim.specialty: ['Internal Medicine', 'Nephrology', 'Rheumatology']
hcp_dim.tier: ['A', 'B', 'C']
fact_rx.brand_code: ['GAZYVA']
fact_rep_activity.activity_type: ['call', 'lunch_meeting']
fact_rep_activity.status: ['cancelled', 'completed', 'scheduled']
fact_payor_mix.payor_type: ['Commercial', 'Medicaid', 'Medicare', 'Other']
territory_dim.geo_type: ['Metro Area', 'State Cluster']

---

TABLE: account_dim

- account_id (INTEGER)
- name (TEXT/VARCHAR) | Values: ['Bay Clinic', 'Bay Hospital', 'Bay Medical Center', 'Mountain Clinic', 'Mountain Hospital', 'Pacific Clinic', 'Pacific Hospital', 'Valley Hospital', 'Valley Medical Center']
- account_type (TEXT/VARCHAR) | Values: ['Clinic', 'Hospital']
- address (TEXT/VARCHAR) | Values: ['Denver, CO', 'Phoenix, AZ', 'Portland, OR', 'San Diego, CA', 'San Francisco, CA', 'Seattle, WA']
- territory_id (INTEGER)

TABLE: date_dim

- date_id (INTEGER)
- calendar_date (TEXT/VARCHAR)
- year (INTEGER)
- quarter (TEXT/VARCHAR) | Values: ['Q1', 'Q2', 'Q3', 'Q4']
- week_num (INTEGER)
- day_of_week (TEXT/VARCHAR) | Values: ['Fri', 'Mon', 'Sat', 'Sun', 'Thu', 'Tue', 'Wed']

---

TABLE: fact_ln_metrics

- entity_type (TEXT/VARCHAR) | Values: ['A', 'H']
- entity_id (INTEGER)
- quarter_id (TEXT/VARCHAR) | Values: ['2024Q4', '2025Q1', '2025Q2', '2025Q3', '2025Q4']
- ln_patient_cnt (INTEGER)
- est_market_share (FLOAT)

---

TABLE: fact_payor_mix

- account_id (INTEGER)
- date_id (INTEGER)
- payor_type (TEXT/VARCHAR) | Values: ['Commercial', 'Medicaid', 'Medicare', 'Other']
- pct_of_volume (FLOAT)

---

TABLE: fact_rep_activity

- activity_id (INTEGER)
- rep_id (INTEGER)
- hcp_id (INTEGER)
- account_id (INTEGER)
- date_id (INTEGER)
- activity_type (TEXT/VARCHAR) | Values: ['call', 'lunch_meeting']
- status (TEXT/VARCHAR) | Values: ['cancelled', 'completed', 'scheduled']
- time_of_day (TEXT/VARCHAR)
- duration_min (INTEGER)

---

TABLE: fact_rx

- hcp_id (INTEGER)
- date_id (INTEGER)
- brand_code (TEXT/VARCHAR) | Values: ['GAZYVA']
- trx_cnt (INTEGER)
- nrx_cnt (INTEGER)

---

TABLE: hcp_dim

- hcp_id (INTEGER)
- full_name (TEXT/VARCHAR)
- specialty (TEXT/VARCHAR) | Values: ['Internal Medicine', 'Nephrology', 'Rheumatology']
- tier (TEXT/VARCHAR) | Values: ['A', 'B', 'C']
- territory_id (INTEGER)

---

TABLE: rep_dim

- rep_id (INTEGER)
- first_name (TEXT/VARCHAR) | Values: ['Casey', 'Jamie', 'Morgan', 'Reese', 'River', 'Sage', 'Taylor']
- last_name (TEXT/VARCHAR) | Values: ['Brown', 'Chen', 'Gonzalez', 'Kim', 'Miller', 'Thomas', 'White', 'Wilson']
- region (TEXT/VARCHAR) | Values: ['Territory 1', 'Territory 2', 'Territory 3']

---

TABLE: territory_dim

- territory_id (INTEGER)
- name (TEXT/VARCHAR) | Values: ['Territory 1', 'Territory 2', 'Territory 3']
- geo_type (TEXT/VARCHAR) | Values: ['Metro Area', 'State Cluster']
- parent_territory_id (FLOAT)

---

- -- POTENTIAL RELATIONSHIPS (Common Columns) ---
Column 'account_id' links: account_dim, fact_payor_mix, fact_rep_activity
Column 'name' links: account_dim, territory_dim
Column 'territory_id' links: account_dim, hcp_dim, territory_dim
Column 'date_id' links: date_dim, fact_payor_mix, fact_rep_activity, fact_rx
Column 'rep_id' links: fact_rep_activity, rep_dim
Column 'hcp_id' links: fact_rep_activity, fact_rx, hcp_dim