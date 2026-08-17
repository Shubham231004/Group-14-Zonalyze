# Zonalyze UI/UX Review Report

Prepared from the perspective of an external review team

Project reviewed: Zonalyze Capstone Prototype

Main screen reviewed: Zonalyze dashboard and related dashboard panels

Date of review: July 14, 2026

Reviewer role: Another project team reviewing the usability, clarity, visual design, and user experience of Zonalyze

---

## 1. Executive Summary

Zonalyze presents a strong and serious dashboard for location feasibility analysis. The product has a clear purpose: help a user choose whether a business idea is suitable for a municipality and catchment radius. The dashboard is not just showing plain numbers. It combines location, demographics, competition, lease cost, demand, model predictions, map evidence, scenario history, and AI-assisted explanations in one workspace.

The strongest part of the project is that Zonalyze tries to explain why a recommendation is being made. The dashboard does not only say whether a location is good or bad. It shows a recommendation card, key strengths, concerns, demand evidence, competition evidence, lease evidence, prediction credibility, map markers, support coverage, and comparison tools. This gives the project more trust than a simple prediction tool.

The second strong part is the scenario-based flow. The user starts by choosing a municipality, selecting a business subcategory, adjusting a catchment radius, and then running an analysis. This makes the dashboard feel goal-based instead of just data-heavy. The user is not forced to understand the full system before starting.

The third strong part is the map and evidence structure. The Geospatial Map tab includes a market map, selected analysis radius, map source, marker count, footfall evidence, address evidence check, and scenario trust gate. These are useful because location decisions are visual. Seeing a selected area and nearby evidence points makes the project easier to understand.

However, the dashboard also has several UX issues that should be improved. The main issue is information overload. After the user finishes the setup flow, the dashboard gives many sections at once: active target, business resolver, diagnostics, model status, five tabs, KPIs, charts, recommendation, map, address check, support gate, evidence cards, benchmark profile, comparison tools, and AI chat. Each feature is useful, but the combined screen can feel heavy for a first-time user.

The second major issue is language clarity. Some labels are easy to understand, such as "Revenue Estimate", "Risk Forecast", "Demand Evidence", and "Compare locations". Other labels are too technical for a normal user, such as "ML.Core", "ENGINE SYNCING", "OSM tags", "proxy", "feature alignment", "structured output", "model files", "raw AI", and endpoint-related wording. The project is technical, but the user experience should hide technical terms unless the user asks for them.

The third major issue is trust clarity. Zonalyze does a good job showing confidence and data quality, but some screen labels weaken that trust. For example, the dashboard uses "Simulated Score" below the feasibility score. The loader also uses a simulated progress sequence with detailed backend steps. If those steps are not tied to real backend progress, the user may feel the system is pretending to do work. For a decision support tool, the interface should be honest about what is real, what is estimated, and what is only a demo/prototype element.

Overall, Zonalyze is a strong capstone dashboard with a clear product idea and many useful features. It is strongest as a decision support workspace for comparing business location scenarios. It needs improvement in readability, user guidance, visual calmness, accessibility, and language simplicity. The product would feel more polished if the first dashboard view focused on one clear recommendation, one explanation, and one next action, while moving technical details into secondary areas.

Overall UX rating from our team: 7.8 out of 10

This score is high because the project has real feature depth, strong evidence thinking, and a well-defined workflow. It is not higher because the interface currently feels too dense, too technical in some areas, and slightly hard for a new user to scan quickly.

---

## 2. Review Scope

Our team reviewed the Zonalyze dashboard experience based on the current frontend and backend structure. We focused mainly on the dashboard because this is the main user-facing area of the project.

The dashboard areas included in this review are:

- Landing and scenario setup screen
- Initial analysis loading screen
- Main dashboard workspace
- Active Target sidebar
- Business Resolver panel
- System Diagnostics panel
- Model Status panel
- Overview tab
- Geospatial Map tab
- Address Evidence Check panel
- Scenario Trust Gate panel
- Evidence Indicators tab
- Benchmarks Profile tab
- Compare Locations tab
- Floating Zonalyze AI Assistant
- Export Report action

We also considered the backend features that the UI connects to, such as:

- Dashboard summary
- Analyze scenario
- Feasibility report export
- Model status
- System validation
- Business resolution
- Operating profile
- Scenario support coverage
- Recommendation decision
- AI scenario chat
- Geospatial market map
- Site address analysis
- Scenario history and comparison
- Municipality and business subcategory catalogs

This review is written from the view of an outside team. We are not reviewing the internal model quality in detail. We are reviewing how the system feels to use, how clear the information is, and how well the dashboard helps a user make a decision.

---

## 3. Product Understanding

Zonalyze appears to be a feasibility decision support system for business location planning. The user selects a municipality, selects a business subcategory, chooses a radius, and receives an analysis that estimates whether the location and business combination is promising.

The product seems designed for users such as:

- Small business owners checking where to open a store
- Entrepreneurs comparing business ideas across municipalities
- Commercial planners looking at demand and competition
- Students or project evaluators reviewing a data-driven prototype
- Local market analysts who want a first-pass view before deeper research

The main value of Zonalyze is not only the final prediction. The main value is that it combines several signals:

- Population and demographics
- Competition pressure
- Revenue estimate
- Feasibility score
- Risk forecast
- Demand evidence
- Lease cost evidence
- Map evidence
- Footfall and transit signals
- Prediction credibility
- Scenario comparison
- AI explanation

This makes the project feel more complete than a simple machine learning result. It feels closer to a decision dashboard.

---

## 4. Main User Journey

The main journey starts with a setup screen.

The user sees the Zonalyze brand, a short product statement, two quick feature cards, and a scenario setup card. The setup card asks for:

- Target Municipality
- Business Subcategory
- Catchment Radius

The default project scenario appears to be:

- Municipality: Kitchener
- Business: Indian Grocery Store
- Radius: 5 km

The user then clicks "Analyze Location Feasibility".

After that, the user sees a loading screen called "Analyzing Feasibility". The loader shows progress and step messages such as:

- Loading Statistics Canada Census demographic datasets
- Connecting to PostgreSQL and retrieving catchment populations
- Running Random Forest estimators
- Resolving competitor nodes from OpenStreetMap Overpass API
- Calculating lease costs and demand proxies
- Compiling recommendation index

After the loader finishes, the user lands in the main dashboard workspace.

The main workspace has:

- A header with the active scenario
- A "Change Scenario" link
- A sync status
- An "Export Report" button
- A left sidebar with target controls and system panels
- A tabbed right workspace
- A floating AI assistant

The tabbed right workspace includes:

- Overview
- Geospatial Map
- Evidence Indicators
- Benchmarks Profile
- Compare Locations

This journey is logical. The user starts with a question, runs an analysis, and then explores the result.

The main issue is that after the analysis finishes, the user may not know what to look at first. The dashboard has a lot of strong information, but it does not clearly guide the user through the best reading order.

---

## 5. Overall UX Rating

### 5.1 Visual Design: 8 out of 10

The visual design is strong and memorable. The dark interface, glowing cyan highlights, cards, charts, and map layout give Zonalyze a serious technical look. It feels like a real product, not a plain class assignment.

The score is not higher because the style can become too heavy. There is a lot of uppercase text, small text, glowing elements, dark panels, and technical styling. This makes the dashboard impressive, but sometimes harder to read.

### 5.2 Ease of Use: 7 out of 10

The setup flow is easy. Choosing a municipality, business, and radius is simple. The main tabs are also clear.

The score is lower because the main dashboard has many panels and terms. A first-time user may not know whether they should start with the recommendation, the KPIs, the map, the evidence indicators, the benchmark profile, or the AI assistant.

### 5.3 Clarity of Information: 7 out of 10

The dashboard gives many helpful explanations. The recommendation card, strengths, concerns, evidence notes, credibility audit, and AI assistant all support clarity.

The score is lower because some wording is too technical. Some metrics also need clearer scale labels. For example, "Demand Index", "Competition Pressure", and "Transit Index" should explain whether higher is better or worse.

### 5.4 Trust and Data Transparency: 8.5 out of 10

This is one of the strongest parts of Zonalyze. The dashboard shows source notes, credibility labels, proxy data, observed data, limitations, and warnings. This is very good for a machine learning product.

The score is not perfect because some labels can reduce trust, such as "Simulated Score" and a simulated loader. These should be made more honest and clear.

### 5.5 Navigation: 6.5 out of 10

The tab navigation inside the dashboard is clear. The user can move between Overview, Map, Evidence, Benchmarks, and Compare Locations.

The score is lower because the app currently exposes only the main dashboard route. Other pages like demographics, risk, business case, and geospatial exist in the project, but their routes are commented out. This means the user cannot visit them directly. Also, the dashboard tabs are not reflected in the URL, so users cannot share a direct link to the map or evidence tab.

### 5.6 Accessibility: 6 out of 10

The dashboard uses good icon support and clear color grouping in many places.

The score is lower because many labels use very small text, muted gray text on dark backgrounds, all-caps wording, and narrow technical fonts. These choices make the dashboard harder to read for users with low vision, screen fatigue, or smaller screens.

### 5.7 Decision Usefulness: 8.5 out of 10

The dashboard is useful because it gives a full decision story. It shows the recommendation, why it was made, what supports it, what weakens it, and what the user can compare next.

The score is not perfect because the main decision is surrounded by too much technical detail. The strongest decision guidance should be easier to find and easier to act on.

---

## 6. What Works Very Well

### 6.1 The product goal is clear

Zonalyze has a clear purpose. It helps users evaluate whether a business location is feasible. This is easy to understand from the setup screen and the dashboard labels.

Why this works:

- The user is not just browsing data.
- The user is answering a practical question: "Should this business work in this area?"
- The selected municipality, business, and radius make the analysis feel focused.

This is one of the strongest parts of the project. Many dashboards fail because they show data without a clear decision. Zonalyze avoids that problem.

### 6.2 The setup flow is simple and focused

The first screen asks for only three things:

- Target Municipality
- Business Subcategory
- Catchment Radius

This is a good design choice. The user does not need to enter many fields before seeing value. The radius slider is also useful because it makes the catchment area feel adjustable and practical.

What is good here:

- The "Analyze Location Feasibility" button is clear.
- The form is short.
- The default scenario helps the user start quickly.
- The municipality and business dropdowns reduce typing errors.
- The catchment radius slider gives the user control without requiring manual calculation.

This screen should stay simple. It is one of the cleanest parts of the experience.

### 6.3 The dashboard keeps the active scenario visible

The main workspace header shows the active scenario using the municipality, business subcategory, and radius. The left sidebar also shows Active Target details.

Why this matters:

- Users can easily remember what scenario they are viewing.
- It reduces confusion when switching tabs.
- It helps users trust that the numbers are tied to the selected scenario.
- It supports comparison work because the current target is always visible.

This is a good dashboard habit and should be kept.

### 6.4 The recommendation card is valuable

The Overview tab starts with a Unified Feasibility Recommendation card when recommendation data is available. This card includes:

- A recommendation summary
- A recommendation label
- Action guidance
- Primary strengths
- Risk factors and concerns

This is very useful because it turns raw data into a decision. A user does not have to inspect every chart before understanding the general result.

What works especially well:

- Strengths and concerns are shown side by side.
- The recommendation label is visually separated with a badge.
- Action guidance gives the user a next step instead of only a score.
- The card appears before the detailed KPIs, which is the right order.

This card should be treated as the main "answer" of the dashboard.

### 6.5 The KPI cards are easy to scan

The Overview tab shows four main cards:

- Total Population
- Feasibility Score
- Revenue Estimate
- Risk Forecast

This is a strong set of metrics. These four values answer the main questions a user will likely ask:

- How many people are in the area?
- How feasible is the business?
- How much monthly net revenue is estimated?
- How risky is the scenario?

The large numbers are easy to notice. The color coding also helps separate positive, warning, and risk states.

### 6.6 The dashboard explains the prediction

The Prediction Explanation Summary and Main Drivers sections are important. They help users understand why the system reached a result.

This is good because machine learning results can feel like a black box. Zonalyze reduces that problem by showing:

- Revenue explanation
- Risk explanation
- Feasibility explanation
- Positive factors
- Negative factors

This makes the dashboard more useful for a capstone review because it shows that the team thought about interpretability, not only prediction output.

### 6.7 The Evidence Indicators tab is one of the most useful sections

The Evidence Indicators tab is strong because it breaks the analysis into practical categories:

- Demand Evidence
- Competition Evidence
- Lease Cost Evidence
- Prediction Credibility Audit

Each evidence card gives a few specific metrics. For example:

- Demand Index
- Customer Pool
- Foot Traffic
- Transit Index
- Competitors
- Density per 10k
- Nearest POI
- Competition Pressure
- Median Lease
- Cost per square foot per year
- Monthly estimate range

This is specific and useful. It helps the user understand what is driving the final recommendation.

### 6.8 The Prediction Credibility Audit is a major strength

The dashboard separates observed real data from estimated proxy data. This is excellent for trust.

Why this is strong:

- Users can see which inputs are more reliable.
- Users can see where estimates are being used.
- The confidence score gives a simple trust signal.
- The data quality discussion protects the product from overclaiming.

For a location feasibility tool, this is very important. Business decisions can have financial risk. A tool should not hide uncertainty.

### 6.9 The Geospatial Map tab fits the product very well

The map is important because location feasibility is naturally spatial. The Market Map includes:

- Selected analysis area
- Radius display
- Evidence markers
- Map source
- Footfall evidence legend
- OpenStreetMap/CARTO fallback if Mapbox token is not present
- Competitor and transit markers
- Center marker

This gives the user a visual understanding of the selected area. The map makes the analysis feel less abstract.

### 6.10 The Address Evidence Check adds practical value

The Address Evidence Check panel lets the user enter a specific storefront or site location. It checks:

- Public geocoding
- Nearby competitors
- Transit access
- Commercial activity evidence
- Address match confidence
- Other geocode candidates
- Warnings

This is a very practical feature. A user may first compare municipalities, but eventually they care about a real address. This panel supports that next step.

This is one of the most product-like features in Zonalyze because it moves from general area analysis to site-level screening.

### 6.11 The Scenario Trust Gate is a smart idea

The Scenario Trust Gate separates what Zonalyze can safely predict from what it can only use for map or evidence support. This is a strong UX concept.

Why this matters:

- It prevents users from assuming all scenarios have equal model support.
- It explains when custom business ideas are limited.
- It gives next steps before stronger trust.
- It makes technical limits visible in a responsible way.

This should stay in the project. It is a good example of ethical design for a prototype.

### 6.12 The Business Resolver gives users flexibility

The Business Resolver lets users choose between:

- Known catalog business
- Custom business idea

This is useful because real users may not always fit neatly into a fixed list. The custom business idea mode can resolve OSM tags for map and competitor evidence.

The best part is that the UI clearly says the ML prediction still uses the selected catalog business until custom financial assumptions are added. This is honest and important.

### 6.13 The Benchmarks Profile gives business planning context

The Benchmarks Profile tab gives estimated operating assumptions for the selected business. It covers areas such as:

- Lease
- Space
- Staffing
- Customer economics
- Utilities
- Marketing

This is useful because feasibility is not only about demand and competition. A business also needs rough cost assumptions.

The profile also shows:

- Confidence
- Cache status
- Source method
- Warnings
- Next data needed
- Limitations

This is good because it does not present the estimates as exact facts.

### 6.14 Compare Locations is a strong decision feature

The Compare Locations tab lets users compare municipalities and radius options. It includes:

- Save Active
- Run Compare
- Saved Scenarios
- Candidate municipalities input
- Radius options input
- Best current option
- Decision score
- Revenue
- Feasibility
- Risk
- Strengths
- Concerns
- Apply to dashboard

This feature supports the real user goal. Users usually do not ask only "Is Kitchener good?" They ask "Is Kitchener better than Waterloo, Cambridge, Guelph, London, or Kingston?" The comparison tab directly supports that.

### 6.15 The AI Assistant is placed where users can ask follow-up questions

The floating Zonalyze AI Assistant provides suggested questions such as:

- Why is this scenario recommended or not recommended?
- What is the biggest risk in this scenario?
- What can I change to improve feasibility?
- Which values are real data and which are estimated?
- How reliable is this prediction?

These are exactly the kind of questions a user may ask after seeing the dashboard. This is a good use of AI because it supports explanation rather than replacing the dashboard.

### 6.16 Export Report is important for real use

The "Export Report" button is useful because users may need to submit, share, or save the result. This is especially important for a capstone project because the generated report can show that the dashboard is not only visual but also produces a business artifact.

---

## 7. Main UX Problems

### 7.1 The main dashboard has too much information at once

The dashboard contains many strong features, but they compete for attention. After analysis, the user sees:

- Header with sync and export
- Active Target
- Business Resolver
- System Diagnostics
- Model Status
- Five tabs
- Recommendation card
- KPI cards
- Charts
- Explanation sections
- AI chat button

This can feel overwhelming.

Why this is a problem:

- First-time users may not know where to start.
- Important information can get lost.
- The user may spend time reading system details before reading the recommendation.
- The dashboard can feel more like an engineering control panel than a business decision tool.

Recommended improvement:

Create a clearer first reading path:

1. Start with the recommendation.
2. Show the top three reasons.
3. Show one next action.
4. Then let the user expand details.

For example, the Overview tab could start with:

- Final recommendation
- Confidence level
- Main reason
- Biggest risk
- Best next action

Then the detailed KPIs, charts, and evidence can come below.

### 7.2 The visual style is impressive but sometimes too intense

The dark "command center" design gives the product a strong identity. However, the scanline, glow effects, small uppercase labels, technical fonts, and many dark cards can make the screen feel busy.

Why this is a problem:

- It can reduce readability.
- It can make normal business users feel like the product is too technical.
- It can make all panels feel equally important.
- It can be tiring during longer use.

Recommended improvement:

Keep the dark theme, but reduce the intensity:

- Use fewer uppercase labels.
- Increase text size in small labels.
- Reduce glow and scanline effects.
- Use more quiet spacing around key sections.
- Make the recommendation card visually calmer and more readable.
- Use color mainly for status, not decoration.

### 7.3 Some user-facing text is too technical

The dashboard uses terms that may be clear to developers but not to normal users.

Examples:

- ML.Core
- ENGINE SYNCING
- System Diagnostics
- Model Status
- Rows
- Accuracy
- OSM tags
- Overpass API
- Proxy
- Raw AI
- Structured output
- Endpoint
- PostgreSQL
- Random Forest estimators
- Cache status
- Feature pipeline

Why this is a problem:

- The user may not know what these terms mean.
- It can make the product feel less approachable.
- It can distract from the business decision.

Recommended improvement:

Use simpler labels in the main UI and keep technical details in tooltips or expandable sections.

Suggested label changes:

| Current label | Suggested label |
|---|---|
| ML.Core | Analysis Engine |
| ENGINE SYNCING | Updating results |
| System Diagnostics | System Check |
| Model Status | Prediction Model |
| Rows | Training Rows |
| Accuracy | Risk Model Accuracy |
| OSM tags | Map search tags |
| Proxy | Estimate |
| Raw AI | Local AI status |
| Cache status | Saved estimate status |
| Simulated Score | Prototype model score |

### 7.4 The simulated loader can reduce trust

The analysis loader uses a progress bar that moves from 0 to 100 with a fixed interval. It also shows detailed backend steps.

Why this is a problem:

- If the progress is not tied to real backend progress, it can feel fake.
- Users may think each step is actually happening live.
- If the backend fails after the loader finishes, the experience may feel confusing.
- The product is trust-aware elsewhere, so the loader should also be honest.

Recommended improvement:

Use a real loading state if possible. If real progress is not available, use a simpler message:

"Preparing scenario results. This may take a few seconds."

Then show the actual result when the backend returns.

If the step messages are kept, label them as "Preparing analysis workflow" instead of implying exact live progress.

### 7.5 "Simulated Score" weakens the feasibility metric

The Feasibility Score card shows the score and then says "Simulated Score".

Why this is a problem:

- The word "simulated" may make users doubt the dashboard.
- It conflicts with the trust-aware evidence layer.
- It is not clear whether the score is model-generated, estimated, or just placeholder data.

Recommended improvement:

Use a more precise label:

- "Prototype model score"
- "Estimated feasibility"
- "Model estimate"
- "Feasibility estimate"

If it is truly simulated, explain that in a small info tooltip rather than under the main number.

### 7.6 The charts need clearer meaning

The Overview tab includes:

- Population Coverage Area
- Demographic Segment Distribution

The Population Coverage Area chart appears to create a trend using population values across artificial time points like 0h, 2h, 4h, and so on. This can be confusing because population is not changing every two hours in the dashboard.

The Demographic Segment Distribution chart combines items like Youth, Families, Seniors, and Diversity. Some may be percentages while diversity may be an index. These are not exactly the same type of value.

Why this is a problem:

- Users may read the population chart as real time activity.
- Users may compare bars that use different units.
- It can weaken trust if the chart looks more real than it is.

Recommended improvement:

Replace the population trend chart with something more directly useful:

- Population by age group
- Customer pool estimate by segment
- Catchment population summary
- Demand, competition, lease, and risk score comparison

For the demographic chart, separate percentage values from index values or clearly label the unit beside each bar.

### 7.7 Some metrics need plain explanations

Several dashboard metrics are useful but need short definitions.

Examples:

- Demand Index
- Foot Traffic
- Transit Index
- Competition Pressure
- Density per 10k
- Risk Forecast
- Decision Score
- Confidence Score

Why this is a problem:

- A user may not know whether higher is better or worse.
- Similar-looking numbers may have different meanings.
- It is hard to make decisions if the scale is unclear.

Recommended improvement:

Add one-line helper text or hover tooltips.

Examples:

- Demand Index: "Higher means stronger expected customer demand."
- Competition Pressure: "Higher means more competitor pressure."
- Lease Cost Pressure: "Higher means rent may be harder to manage."
- Confidence Score: "Higher means Zonalyze has stronger data support for this scenario."
- Decision Score: "A combined score using feasibility, revenue, risk, and confidence."

### 7.8 The custom business flow is useful but easy to misunderstand

The Business Resolver is a strong feature, but the flow is complex. The user can select a known catalog business or enter a custom business idea. A custom business can affect map evidence, but the ML prediction still uses the selected catalog business until custom assumptions are added.

Why this is a problem:

- A user may think the custom business changes everything.
- The difference between "map evidence" and "ML prediction" is not simple.
- The current explanation is honest but long and technical.

Recommended improvement:

Show a simple status summary after custom resolution:

"This custom business is being used for map evidence only. The prediction still uses Indian Grocery Store."

Use a visual split:

- Prediction: Catalog business
- Map evidence: Custom business

This would make the behavior much easier to understand.

### 7.9 The left sidebar mixes user controls with developer tools

The left sidebar contains:

- Active Target
- Business Resolver
- System Diagnostics
- Model Status

The Active Target and Business Resolver are user-facing. System Diagnostics and Model Status feel more like developer or demo tools.

Why this is a problem:

- It gives equal space to user tasks and technical status.
- It can distract from the decision.
- A business user may not need system diagnostics during normal use.

Recommended improvement:

Move System Diagnostics and Model Status into a smaller "System" drawer, footer, or admin section.

Keep the sidebar focused on:

- Current scenario
- Edit radius
- Business input mode
- Change scenario

For a capstone demo, diagnostics are useful. But they should not compete with the main decision workflow.

### 7.10 Navigation is limited to one active route

The app currently routes only to the dashboard at `/`. Other pages exist in the project, such as demographics, risk, business case, and geospatial, but their routes are commented out.

Why this is a problem:

- Users cannot open specific pages directly.
- Users cannot share a direct link to a dashboard section.
- Browser back and forward buttons do not help with tab changes.
- The app looks smaller than the codebase suggests.

Recommended improvement:

Add route support for dashboard tabs or re-enable the other pages if they are ready.

Suggested route structure:

- `/` or `/dashboard`
- `/dashboard/overview`
- `/dashboard/map`
- `/dashboard/evidence`
- `/dashboard/benchmarks`
- `/dashboard/compare`

This would make the app feel more complete and easier to present.

### 7.11 The Address Evidence Check has a different visual style

Most dashboard panels use a dark style. The Address Evidence Check uses a white card with slate text.

Why this is a problem:

- It looks visually separate from the rest of the dashboard.
- It may feel like a component from another design system.
- It breaks the dark workspace rhythm.

Recommended improvement:

Restyle the Address Evidence Check to match the dashboard:

- Dark panel background
- Same border style
- Same text size system
- Same badge style
- Same spacing as Scenario Trust Gate

The feature itself is useful. The issue is only visual consistency.

### 7.12 The AI Assistant button may not be clear enough

The floating AI button uses an icon and title text on hover. The chat window itself is useful, but the closed button does not have visible text.

Why this is a problem:

- Some users may not notice what the button does.
- On mobile, hover title is not useful.
- The floating button may cover content near the bottom right.

Recommended improvement:

Use a slightly wider button with text:

"Ask AI"

Or show a small label beside the button after the first analysis:

"Ask about this result"

This would make the assistant easier to discover.

### 7.13 Compare Locations should require at least two saved scenarios for history comparison

The history comparison button is disabled when scenario history length is less than 1. However, a meaningful comparison needs at least two scenarios.

Why this is a problem:

- A user may save one scenario, click compare, and then receive a "Save more scenarios" message.
- It is better to prevent the action until it can succeed.

Recommended improvement:

Disable "Run Compare" until there are at least two saved scenarios.

Show helper text:

"Save at least two scenarios to compare them."

This is a small fix that would make the interface feel more polished.

### 7.14 Export Report needs more context

The Export Report button is useful, but the user does not see what will be included before exporting.

Why this is a problem:

- The user may not know whether the report uses the latest dashboard state.
- The user may not know the file type.
- The user may not know if map evidence or benchmark profile is included.

Recommended improvement:

Add a small report preview or menu:

- "Export current scenario"
- "Includes recommendation, evidence, credibility, and key metrics"
- "File type: text report"

If the export is plain text, consider offering PDF or Word export later.

### 7.15 Some text is too small

Many labels use very small text sizes such as 9px, 10px, and 11px. This is visible in dashboard labels, tabs, badges, cards, and system sections.

Why this is a problem:

- Small text is hard to read on laptops and mobile screens.
- All-caps small text is even harder to scan.
- Low-contrast gray text on dark panels can fail readability expectations.

Recommended improvement:

Use 12px as the minimum for secondary labels and 14px for normal body text. Keep 10px text only for optional metadata that is not required for decision making.

### 7.16 The dashboard needs stronger empty and error states

The dashboard has some error messages and toasts, but several sections rely on "N/A", missing data, or backend failure states.

Why this is a problem:

- A user may not know whether "N/A" means loading, unavailable, not supported, or failed.
- Toasts can disappear before the user reads them.
- If backend services are unavailable, the dashboard may feel broken instead of guided.

Recommended improvement:

Use clearer empty states:

- "No lease evidence found for this scenario."
- "Map evidence could not be loaded. Try again."
- "AI assistant is unavailable because the local AI service is not running."
- "Prediction data is unavailable. Check backend connection."

Each empty state should include the next action.

### 7.17 The wording sometimes sounds more technical than user-centered

Several sections describe the system from the developer's view instead of the user's view.

Example:

"The resolver calls the backend /business/resolve endpoint and uses local AI structured output when available."

This is accurate, but most users do not need endpoint names.

Recommended improvement:

Change it to:

"Zonalyze checks your business idea and finds matching map categories when possible."

Keep endpoint details in documentation or developer mode.

---

## 8. Screen-by-Screen Review

## 8.1 Landing and Scenario Setup Screen

### What the screen does

This screen introduces Zonalyze and lets the user create the first scenario. It shows the logo, product name, a version badge, the phrase "Decision Support System", a headline about evaluating location feasibility, two feature cards, and the setup form.

### What works well

The form is simple. It asks for only the minimum information needed:

- Municipality
- Business subcategory
- Radius

The "Analyze Location Feasibility" button is clear and action-focused.

The two feature cards, Demographics and Competitors, quickly tell the user what kind of data will be used.

The layout has a strong first impression. It feels polished and designed.

### What needs improvement

The headline and supporting text use phrases such as "data-driven decisions powered by machine learning algorithms." This is understandable, but it could be more direct.

Suggested rewrite:

"Check whether a business idea fits a local area using population, competition, demand, rent, and risk signals."

The setup card should also show what happens after analysis. For example:

"You will get a recommendation, key risks, evidence details, and a map."

This would make the user more confident before clicking.

### Recommended priority

Medium priority. The screen is already strong, but clearer wording would make it feel more human.

---

## 8.2 Analysis Loading Screen

### What the screen does

The loading screen appears after the user starts analysis. It shows a logo, progress bar, current loading step, and "Zonalyze Engine Processing".

### What works well

The loading screen makes the system feel active. It gives the user feedback instead of leaving a blank screen.

The step messages explain what kinds of data the system uses, such as census data, competitor data, lease costs, demand proxies, and recommendation logic.

### What needs improvement

The loading progress is simulated. It uses fixed progress increments and step changes. This can reduce trust if users think the progress is real.

The phrase "Running advanced geospatial and ML algorithms" is a little broad. The rest of the product is careful about evidence and limits, so the loader should also be careful.

Suggested rewrite:

"Preparing the scenario analysis. Zonalyze is collecting available data, updating map evidence, and building the recommendation."

### Recommended priority

High priority. Since the product is trust-focused, the loader should not look like fake progress.

---

## 8.3 Main Header

### What the screen does

The header shows:

- Zonalyze ML.Core
- Active scenario badge
- Change Scenario
- Sync status
- Export Report

### What works well

The active scenario is visible, which is very helpful.

The "Change Scenario" action is placed near the scenario label, which makes sense.

The "Export Report" button is easy to find.

### What needs improvement

"ML.Core" and "ENGINE SYNCING" sound technical. For a normal user, "Analysis Engine" and "Updating results" would be clearer.

The sync status includes a time, which is useful. However, the label could be more natural:

"Updated at 3:42 PM"

instead of:

"SYNCED: 3:42 PM"

### Recommended priority

Medium priority. The header works, but simple wording would improve confidence.

---

## 8.4 Left Sidebar

### What the sidebar does

The left sidebar includes:

- Active Target
- Radius adjustment
- Business Resolver
- System Diagnostics
- Model Status

### What works well

The Active Target card is useful. It shows location, business, and radius in one place.

The radius slider is helpful because the user can adjust the scenario without going back to the setup screen.

The Business Resolver is a valuable feature because it supports custom business ideas.

### What needs improvement

The sidebar is too crowded. The Business Resolver is large and complex. System Diagnostics and Model Status add even more content.

The sidebar mixes user tasks with system health details. A business user mainly needs scenario controls. The model rows and validation checks are useful for a demo, but not for everyday decision making.

Recommended layout:

- Keep Active Target and Business Input in the sidebar.
- Move System Diagnostics and Model Status into a collapsed "System details" area.
- Put detailed business resolver explanations behind "Learn more".

### Recommended priority

High priority. The sidebar affects the whole dashboard experience.

---

## 8.5 Overview Tab

### What the tab does

The Overview tab shows the main recommendation, KPIs, charts, prediction explanation, and main drivers.

### What works well

This tab has the right overall purpose. It gives the user the main answer first.

The recommendation card is very strong because it includes strengths, concerns, and action guidance.

The four KPI cards are clear and useful.

The main drivers section helps explain the result.

### What needs improvement

The charts need clearer meaning. The population chart looks like a time trend, but it is built from population data. This can confuse users.

The demographic chart mixes different kinds of values. Youth, families, and seniors may be percentages, while diversity is an index.

The "Simulated Score" label should be changed.

Recommended layout:

1. Recommendation card
2. Four KPI cards
3. "Why this result?" explanation
4. Main drivers
5. Clear chart section with properly labeled data

### Recommended priority

High priority. The Overview tab is the most important tab.

---

## 8.6 Geospatial Map Tab

### What the tab does

The Geospatial Map tab shows the market map, selected radius, footfall evidence, address evidence check, and scenario trust gate.

### What works well

The map is very relevant to the product. The selected area, markers, map source, and evidence count make the location feel real.

The footfall legend is useful and visually clear.

The address evidence check adds practical site-level screening.

The scenario trust gate is a strong trust feature.

### What needs improvement

The map uses red for the selected area and competitors. Red can suggest danger. If the selected radius is red, the user may think the whole area is bad.

The map should include a clearer marker legend:

- Center location
- Competitor
- Transit
- Footfall evidence
- Selected radius

The Address Evidence Check should match the dark dashboard style.

The map source note is useful, but "Mapbox GL JS" and "OpenStreetMap/CARTO tiles" can be placed in a small source area instead of the main reading path.

### Recommended priority

Medium to high priority. The map is strong, but clearer legends and styling would make it easier to use.

---

## 8.7 Evidence Indicators Tab

### What the tab does

This tab shows demand, competition, lease cost, and prediction credibility.

### What works well

This is one of the best sections. It supports the final recommendation with clear evidence groups.

The three-card layout is easy to scan:

- Demand
- Competition
- Lease

The credibility audit is also excellent because it separates observed real data and estimated proxy data.

### What needs improvement

The cards need small definitions for metrics. For example, "Density / 10K" should explain competitors per 10,000 people. "Comp. Pressure" should avoid abbreviation.

Some labels use very small text. The evidence notes are important, so they should be easier to read.

The word "Proxy" may be too technical. Consider using "Estimate" in the user interface and explaining proxy in a tooltip or trust section.

### Recommended priority

Medium priority. The section is already strong, but plain labels would improve it.

---

## 8.8 Benchmarks Profile Tab

### What the tab does

This tab shows AI-generated planning ranges for operating assumptions.

### What works well

The tab covers important business planning areas. It helps users understand rent, space, staffing, customer economics, utilities, and marketing.

The profile includes confidence and limitations, which is responsible.

The "Refresh profile" action is clear.

### What needs improvement

The phrase "AI Benchmark Operating Profile" may sound technical or uncertain to some users. It is honest, but it could be friendlier.

Suggested label:

"Operating Cost Benchmarks"

The tab should also clearly state:

"These are planning estimates, not quotes."

This message exists in the text, but it should be shorter and more visible.

### Recommended priority

Medium priority. The feature is useful, but the wording can be simpler.

---

## 8.9 Compare Locations Tab

### What the tab does

This tab supports saved scenario comparison and location comparison across candidate municipalities and radius options.

### What works well

The feature matches the real user goal very well. Users usually want to compare options before deciding.

The "Best current option" card is strong.

The ranking table includes useful columns:

- Rank
- Location
- Score
- Revenue
- Feasibility
- Risk

The "Apply to dashboard" button is very helpful because it turns comparison into action.

### What needs improvement

Candidate municipalities and radius options are typed into plain text fields separated by commas. This is flexible, but it can cause input errors.

Recommended improvement:

- Use chips/tags for selected municipalities.
- Provide add/remove controls.
- Validate unsupported municipality names before comparison.
- Show clear feedback for invalid radius values.

The "Run Compare" history action should require at least two saved scenarios.

### Recommended priority

Medium priority. The feature is strong, but input handling can be improved.

---

## 8.10 Floating AI Assistant

### What it does

The AI Assistant answers questions about the current scenario. It shows suggested questions, a text area, an AI status badge, model badge, answer, used signals, and limitations.

### What works well

The suggested questions are very helpful. They match what users will naturally wonder after viewing results.

The assistant shows used signals and limitations. This is better than a chat box that gives answers without context.

### What needs improvement

The closed button should be more discoverable. A visible "Ask AI" label would help.

The suggested question buttons use truncation. Some questions may be cut off, especially on smaller screens.

If AI is unavailable, the message should be friendly and actionable:

"AI assistant is not available right now. The dashboard results are still usable."

### Recommended priority

Medium priority. The feature is useful, but discovery and fallback states should be clearer.

---

## 9. Accessibility Review

### 9.1 Text size

Many labels are very small. Some are 9px, 10px, or 11px. This makes the dashboard harder to read.

Recommended change:

- Minimum body text: 14px
- Minimum secondary label text: 12px
- Avoid 9px text except for non-essential metadata

### 9.2 Contrast

The dashboard uses dark backgrounds with muted gray text. This looks clean, but some text may be too faint.

Recommended change:

- Increase contrast for labels and notes.
- Use muted text only for optional information.
- Make data quality notes easier to read.

### 9.3 All-caps text

The dashboard uses a lot of uppercase text. Uppercase works for short badges but becomes hard to scan when used everywhere.

Recommended change:

- Use title case for normal headings.
- Keep uppercase only for small badges or status labels.

### 9.4 Color meaning

The dashboard uses green, yellow, red, cyan, amber, and rose colors. These are useful, but color should not be the only way to show meaning.

Recommended change:

- Add labels such as Low, Medium, High.
- Add short text explanations beside color badges.
- Use icons or words with color status.

### 9.5 Keyboard and focus visibility

The dashboard uses buttons, select controls, sliders, and tabs. Focus states should be clear for keyboard users.

Recommended change:

- Make sure every button, tab, input, and chat control has a visible focus style.
- Make the floating AI close button easy to reach by keyboard.
- Make tab order follow the visual layout.

---

## 10. Mobile and Responsive Experience

The layout uses responsive grids and should collapse on smaller screens. This is good. However, the amount of content may still make mobile use difficult.

Likely mobile issues:

- The left sidebar content becomes long.
- The Business Resolver panel has a lot of text.
- The tab bar may require horizontal scrolling.
- The map and legends may take most of the screen.
- The floating AI button may cover content.
- Small labels may become harder to read.

Recommended mobile improvements:

- Collapse the left sidebar into a "Scenario settings" drawer.
- Keep the recommendation card at the top.
- Make tabs sticky or use a dropdown on mobile.
- Move System Diagnostics and Model Status out of the main mobile flow.
- Let the AI button move above bottom content or become a smaller "Ask" tab.

---

## 11. Content and Language Review

Zonalyze has strong content, but it should be written more for the user and less for the developer.

### Strong examples

These labels are clear:

- Target Municipality
- Business Subcategory
- Catchment Radius
- Analyze Location Feasibility
- Revenue Estimate
- Risk Forecast
- Demand Evidence
- Competition Evidence
- Lease Cost Evidence
- Address Evidence Check
- Compare locations
- Save Active
- Apply to dashboard

### Labels that should be simplified

These labels are too technical:

- ML.Core
- ENGINE SYNCING
- System Diagnostics
- Prediction Credibility Audit
- Proxy Estimated Inputs
- OSM tags
- Raw AI
- Model Status
- Cache status

Suggested simpler versions:

- Analysis Engine
- Updating results
- System Check
- Prediction Confidence
- Estimated Data
- Map search tags
- Local AI
- Prediction Model
- Saved estimate status

### Tone recommendation

The interface should sound confident but careful.

Good tone:

"This scenario looks promising because demand is strong and competition pressure is manageable. Lease cost is still a concern, so verify rent before making a final decision."

Avoid:

"Running advanced ML algorithms for data-driven feasibility intelligence."

The first version is easier to trust because it is direct.

---

## 12. Trust and Transparency Review

Trust is one of Zonalyze's best areas. The project already includes:

- Confidence levels
- Data quality notes
- Observed real data
- Estimated proxy data
- Warnings
- Limitations
- Scenario support coverage
- AI limitations
- Source method labels

This is excellent.

The main recommendation is to make trust language simpler and more visible.

For example, the dashboard could show a small trust summary beside the recommendation:

"Confidence: Moderate. Strong demographic data. Some demand and lease values are estimated."

This would help users understand the trust level before reading the detailed audit.

The system should also clearly separate:

- Real observed data
- Model prediction
- Estimate
- AI-generated benchmark
- Missing data

This is already partly done. The next step is to make those categories easier to understand without reading long notes.

---

## 13. Information Architecture Review

The dashboard uses five main tabs:

- Overview
- Geospatial Map
- Evidence Indicators
- Benchmarks Profile
- Compare Locations

This is a good structure. The tab names mostly match user tasks.

Suggested tab changes:

| Current tab | Suggested tab |
|---|---|
| Overview | Overview |
| Geospatial Map | Map |
| Evidence Indicators | Evidence |
| Benchmarks Profile | Cost Benchmarks |
| Compare Locations | Compare |

The current names are not wrong. The shorter names would be easier to scan.

Recommended reading order:

1. Overview: What is the answer?
2. Evidence: Why did the answer happen?
3. Map: Where is the opportunity or pressure?
4. Cost Benchmarks: What assumptions should we check?
5. Compare: Is another location better?

This order should be reflected in the interface. The current order is close, but "Map" comes before "Evidence". That is okay because maps are central to location analysis. Still, the user should be guided to evidence when they need reasoning.

---

## 14. Detailed Improvement Plan

## 14.1 High-priority improvements

### Improvement 1: Simplify the first dashboard view

Problem:

The Overview tab has many items and can feel heavy.

Fix:

Make the first part of Overview show only:

- Final recommendation
- Confidence
- Top reason
- Biggest risk
- Next action

Reason:

Users need the answer first. Details should support the answer, not compete with it.

### Improvement 2: Replace or relabel the simulated loader

Problem:

The loader looks like real progress but is simulated.

Fix:

Use a general loading message or connect progress to real backend events.

Reason:

Trust matters in a decision tool. Fake progress can make users doubt the system.

### Improvement 3: Change technical wording to user wording

Problem:

Some labels sound like backend or developer language.

Fix:

Replace technical labels with plain labels and move technical details to tooltips.

Reason:

The user should focus on the business decision, not the internal system.

### Improvement 4: Improve small text readability

Problem:

Many labels are too small.

Fix:

Increase minimum text size and reduce all-caps usage.

Reason:

Readable text is a basic part of good UX.

### Improvement 5: Clarify custom business behavior

Problem:

Custom business input affects map evidence but not the ML prediction.

Fix:

Show a simple status box:

"Prediction uses catalog business. Map evidence uses custom business."

Reason:

This prevents wrong assumptions about the result.

---

## 14.2 Medium-priority improvements

### Improvement 6: Add tab routes

Problem:

Dashboard tabs are not shareable as links.

Fix:

Use routes such as `/dashboard/map` and `/dashboard/evidence`.

Reason:

This improves navigation, sharing, and presentation.

### Improvement 7: Improve metric definitions

Problem:

Some metrics do not explain their scale.

Fix:

Add helper text or tooltips.

Reason:

Users need to know what a number means before acting on it.

### Improvement 8: Make the map legend clearer

Problem:

Map colors and markers need clearer meaning.

Fix:

Add a simple legend for center, competitors, transit, selected radius, and footfall.

Reason:

Maps are easier to trust when symbols are explained.

### Improvement 9: Restyle Address Evidence Check

Problem:

The white card does not match the dark dashboard.

Fix:

Use the same dark panel style as the other map tab cards.

Reason:

Visual consistency makes the product feel more complete.

### Improvement 10: Improve Compare Locations inputs

Problem:

Comma-separated text fields can cause input mistakes.

Fix:

Use chips/tags for municipalities and radius options.

Reason:

Users can see and edit each comparison item clearly.

---

## 14.3 Lower-priority improvements

### Improvement 11: Add report export preview

Problem:

The user does not know what the export includes.

Fix:

Show a small preview or export menu.

Reason:

This makes the export feel more reliable.

### Improvement 12: Improve AI assistant discovery

Problem:

The floating icon may not be obvious.

Fix:

Add visible text such as "Ask AI".

Reason:

The assistant is useful, so users should notice it.

### Improvement 13: Move diagnostics into a secondary area

Problem:

Diagnostics are useful but not central to the user goal.

Fix:

Move them into a collapsed admin/system section.

Reason:

The main dashboard should focus on the location decision.

---

## 15. Suggested Revised Dashboard Flow

A cleaner dashboard flow could look like this:

### Step 1: Scenario Setup

User selects:

- Municipality
- Business
- Radius

Then clicks:

"Analyze location"

### Step 2: Result Summary

The top of the dashboard shows:

- Recommendation
- Confidence
- Expected monthly revenue
- Feasibility score
- Risk
- Main reason
- Biggest concern
- Next action

### Step 3: Explore Details

Tabs show:

- Evidence
- Map
- Costs
- Compare

### Step 4: Ask or Export

User can:

- Ask AI
- Export report
- Save scenario
- Compare another location

This flow keeps the project's existing features but gives them a more natural order.

---

## 16. Best Parts to Highlight in the Submission

If presenting Zonalyze to instructors or another team, we recommend highlighting these parts:

### 16.1 Trust-aware recommendation system

Zonalyze does not only provide a prediction. It explains the confidence, data quality, observed inputs, proxy estimates, and next data needed.

Why this is impressive:

It shows responsible design. The team understands that predictions should not be treated as perfect facts.

### 16.2 Scenario-based business feasibility workflow

The user can select municipality, business type, and radius, then receive a focused recommendation.

Why this is impressive:

It makes the product practical and easy to demo.

### 16.3 Geospatial market map

The map includes radius, evidence markers, source notes, footfall evidence, and fallback map support.

Why this is impressive:

It connects the analysis to real geography and makes the result easier to understand.

### 16.4 Evidence Indicators tab

Demand, competition, lease cost, and credibility are separated into clear sections.

Why this is impressive:

It shows that the team did not rely on one score only. The decision is supported by several evidence layers.

### 16.5 Scenario comparison

The user can compare locations and apply the best option back to the dashboard.

Why this is impressive:

It turns the dashboard into a decision tool, not just a report screen.

### 16.6 AI Assistant with limitations

The assistant can answer questions about the scenario and shows used signals and limitations.

Why this is impressive:

It uses AI in a helpful way while still keeping the dashboard evidence visible.

---

## 17. Main Weaknesses to Mention Honestly

The project should also be honest about areas that need improvement.

### 17.1 The dashboard is dense

There are many panels and technical sections. New users may need guidance.

### 17.2 Some labels are too technical

The interface sometimes uses system language instead of user language.

### 17.3 Some visuals need clearer meaning

The charts and map markers need clearer labels and legends.

### 17.4 Accessibility needs improvement

Small text, low contrast, and heavy uppercase styling can reduce readability.

### 17.5 The loader should not imply fake precision

If progress is simulated, the UI should not make it look like exact backend progress.

### 17.6 Some routes are not active

The app currently exposes only the main dashboard route, even though other page components exist.

---

## 18. Specific Recommendations for Final Polish

These are concrete changes we recommend before final submission:

1. Rename "Simulated Score" to "Prototype model score" or "Estimated feasibility".

2. Rename "ENGINE SYNCING" to "Updating results".

3. Rename "ML.Core" to "Analysis Engine".

4. Change the loading message so it does not look like fake exact progress.

5. Add a short "How to read this result" line below the recommendation card.

6. Add helper text for Demand Index, Competition Pressure, Lease Cost Pressure, and Confidence Score.

7. Move System Diagnostics and Model Status into a collapsed section.

8. Add a map legend for center marker, competitors, transit, footfall, and selected radius.

9. Restyle Address Evidence Check to match the dark dashboard.

10. Disable history comparison until at least two scenarios are saved.

11. Add visible text to the floating AI button.

12. Increase small labels from 9-10px to at least 12px.

13. Reduce all-caps usage in long labels.

14. Add direct routes for dashboard tabs.

15. Add an export preview or short export description.

16. Replace the population trend chart with a more meaningful chart.

17. Separate percentages from indexes in the demographic chart.

18. Show a clear message when custom business affects only map evidence, not the prediction.

---

## 19. Final Review Statement

From our team's perspective, Zonalyze is a strong and well-built capstone prototype. It has a clear purpose, useful features, and a strong evidence-based approach. The dashboard shows real thought about how users make location decisions. The recommendation card, evidence indicators, credibility audit, map, address check, benchmark profile, comparison tools, and AI assistant all support the main goal.

The biggest improvement needed is not adding more features. The biggest improvement is making the existing features easier to read, easier to trust, and easier to follow. Zonalyze already has enough depth. It now needs a calmer user flow, simpler wording, clearer metric definitions, better accessibility, and stronger guidance for first-time users.

If these improvements are made, Zonalyze would feel less like a technical demo and more like a polished decision support product. The project already has the right foundation. The next step is to help users understand the result faster and act on it with more confidence.

---

## 20. Appendix: Quick Rating Table

| Area | Rating | Reason |
|---|---:|---|
| Product idea | 9/10 | Clear, practical, and useful for business location decisions. |
| First screen | 8/10 | Strong setup flow, but wording can be more direct. |
| Main dashboard layout | 7/10 | Powerful but dense. Needs stronger reading order. |
| Visual design | 8/10 | Polished and memorable, but intense and small in places. |
| Recommendation clarity | 8.5/10 | Strong strengths, concerns, and action guidance. |
| Evidence transparency | 9/10 | Excellent use of credibility, observed data, and estimates. |
| Map experience | 8/10 | Very useful, needs clearer legend and color meaning. |
| Comparison tools | 8/10 | Strong decision feature, input controls can improve. |
| AI assistant | 7.5/10 | Helpful suggested questions, needs better discovery. |
| Accessibility | 6/10 | Needs larger text, better contrast, and less all-caps styling. |
| Navigation | 6.5/10 | Tabs are clear, but route support is limited. |
| Overall UX | 7.8/10 | Strong feature set and trust design, needs simplification and polish. |

