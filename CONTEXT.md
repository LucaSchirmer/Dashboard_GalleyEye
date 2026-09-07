# GalleyEye

GalleyEye supports airline catering planning by relating what passengers were served to what they consumed on a specific flight.

## Language

**Catering Planner**:
The airline or catering-operations specialist who uses observed serving and consumption results to plan future catering quantities and portion sizes.
_Avoid_: Dashboard user, operator

**Flight Service**:
One actual occurrence of a flight for which catering service is analyzed. Different Flight Services can be selected individually for analysis.
_Avoid_: Flight pattern, route

**Comparable Flight Group**:
Flight Services with the same travel direction whose combined observations provide the evidence for a Decision-Support Recommendation. Departure period remains descriptive and filterable but does not determine membership.
_Avoid_: Selected flight, route total

**Comparable Group Flight Count**:
The number of Flight Services in a Comparable Flight Group, whether or not every Flight Service contributes Consumption Observations for a particular Served Item.
_Avoid_: Evidence flight count, observed flight count

**Observation-Contributing Flight Count**:
The number of distinct Flight Services in a Comparable Flight Group that contribute at least one Consumption Observation for a particular Served Item.
_Avoid_: Comparable group size, observation count

**Served Item**:
A food or beverage item given to a passenger during a Flight Service.
_Avoid_: Order, ordered item, loaded item

**Loaded Item**:
A food or beverage item placed aboard for a Flight Service, whether or not it is later served to a passenger.
_Avoid_: Served item, ordered item

**Reference Image**:
An image of an unconsumed tray configuration used as the comparison baseline for one or more Consumption Images. It does not represent the physical earlier state of each compared tray.
_Avoid_: Before image, outgoing tray

**Consumption Image**:
An image of a tray after passenger consumption, from which the consumed proportion of its Served Items is estimated.
_Avoid_: After image, returned half of a tray pair

**Consumption Estimate**:
The model-predicted percentage of a Served Item's initial food mass that a passenger consumed, inferred visually by comparing a Consumption Image with a Reference Image.
_Avoid_: Ground truth, measured consumption

**Consumption Observation**:
One Consumption Estimate for one Served Item detected in a Consumption Image. Observations are aggregated to analyze consumption without implying a physical pairing between Reference and Consumption Images.
_Avoid_: Tray pair, ground-truth measurement

**Unserved Mass**:
The mass of Loaded Items that were not served during a Flight Service.
_Avoid_: Consumption waste

**Consumption Waste**:
The estimated mass of the served portions that passengers did not consume.
_Avoid_: Unserved stock, avoidable carried mass

**Food Value Waste**:
The simulated procurement value of Unserved Mass plus the unconsumed fraction of served portions.
_Avoid_: Realized financial loss, fuel cost

**Avoidable Carried Mass**:
The estimated mass that accepted quantity and portion-size recommendations would remove from a future comparable Flight Service.
_Avoid_: Total loaded mass, current waste

**Decision-Support Recommendation**:
An evidence-based suggestion to a Catering Planner about changing a Served Item's future quantity or portion size, including the estimated effect on carried weight and fuel use. It informs rather than authorizes a catering change.
_Avoid_: Optimization command, automatic decision

**Simulated Direct CO₂ Effect**:
The planning estimate obtained by applying the versioned conventional Jet-A/Jet-A1 direct-combustion factor to Estimated Fuel Savings. It covers tank-to-wake CO₂ only and is neither measured nor realized, nor a lifecycle CO₂e or total climate-impact estimate.
_Avoid_: Emissions reduction, lifecycle emissions, CO₂e saving, climate benefit
