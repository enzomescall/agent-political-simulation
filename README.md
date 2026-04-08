# **Technical Overview**

A turn-based political simulation of a fictional federal democracy. The player is always a politician, starting at a low office and navigating upward through elections, coalition-building, and political consequence. The world simulates around them whether they act or not.

## **The Country**

A compressed federal republic with three tiers of government:

* **Federal**: a president and a congress  
* **States**: 6 states, each with a governor and a state assembly  
* **Municipalities**: \~180 total (\~30 per state), each with a mayor and a municipal chamber (câmara de vereadores)

Every elected position is held by a politician agent. Every politician belongs to a party.

## **Agents**

The core simulated entity is the **politician**. Every elected official is an agent with the following attributes:

* **Ideology**: a 2D position on economic (left/right) and social (progressive/conservative) axes  
* **Allegiances**: a weighted map to interest groups, representing who they identify with and who funds them  
* **Relationships**: a map to other politicians representing political trust — not personal friendship, but realpolitik alignment  
* **Popularity**: approval scores broken down by interest group  
* **Party standing**: how loyal vs. rebellious they are within their party  
* **Ambition/temperature**: drives risk-taking behavior

When a politician makes a decision — voting on a bill, taking a public position, allocating budget — they run a weighted calculation across ideology alignment, party directive, interest group pressure, electoral calculus, and relationship cost. The weights vary by archetype (loyalist, populist, ideologue).

Interest group agents (union leaders, party financiers, rural organizers) are also politicians or politician-adjacent actors with high allegiance to a specific group. They operate both inside politics and as external pressure vectors.

## **Places**

Places are the geographic and administrative containers for government. There are three levels:

* **Federal** (one): hosts the presidency and congress  
* **State** (6): hosts a governor and state assembly  
* **Municipality** (\~180): hosts a mayor and câmara de vereadores

Each place has an executive (one elected head \+ cabinet) and a legislative (a body of elected seats). Interest group presence and satisfaction are local.

## **Parties**

Five parties span the ideological space. No party wins outright federal majorities. Parties have:

* An ideological position on both axes  
* A base constituency (dynamically tied to interest groups, not fixed)  
* Internal structure: a loyalist/rebel spectrum among their members

A politician's relationship with their party is consequential. Voting against the party line costs standing. Winning elections for the party builds it. Low standing risks expulsion; high standing opens paths to party leadership.

## **Interest Groups**

Three baseline groups: **rural workers**, **urban workers**, and **wealthy elites**. Each group:

* Has a set of policy preferences and fears  
* Has a satisfaction score *per place*, driven by local policy outcomes  
* Represents a share of the electorate *per place*  
* Applies pressure on politicians proportional to dissatisfaction and local strength

Groups do not act directly: they influence a politician’s decision-making as a weighted input, and drive electoral behavior at election time.

## **Level of Detail**

The simulation scales agent fidelity based on political relevance to the player, not geography. There are four tiers:

* **L0**: key figures the player directly interacts with — full simulation, potential LLM-enhanced dialogue  
* **L1**: all politicians in the player's state plus national leadership — full weight-based decisions each turn  
* **L2**: politicians in neighboring or relevant states — party-level behavior, individual rolls for major events  
* **L3**: everyone else — pure aggregate statistics, no individual simulation

The LOD boundary shifts when the player changes office, party, or coalition. Becoming a governor pulls an entire state up to L1.

## **Consequence Systems**

The simulation tracks three consequence dimensions:

* **Electoral popularity**: approval scores shift with every decision. At election time, approval plus party brand plus coalition endorsements determines vote share. The player can lose their seat.  
* **Relationships and coalitions**: every interaction updates bilateral trust scores. Governing coalitions require maintaining enough allied legislators above a threshold. Coalition collapse triggers a crisis.  
* **Party standing**: a continuous score that opens or closes internal party paths. Expulsion is possible and survivable but costly.

Upward mobility emerges from these three systems rather than being a fixed progression.

