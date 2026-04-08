## ALWAYS REMINDER: FOCUS ON CLEAN, CONCISE, READABLE CODE. WE DO NOT CARE ABOUT BACKWARDS COMPATABILITY OR EXCESSIVE FALLBACKS

Focus on this development cycle: the Action economy and how agents determine their next steps
1. When looking at their available actions, the agents need to score each of them 
2. We should generate a set of policies at the level of the legislature, and then the members of the chamber should then assess the options at hand and choose to push one forward to a vote or not. They should try and predict the outcome of a vote, and then predict the consequences of losing or winning the vote.
3. The agent should estimate the consequences of each action and choose whichever will bring them the most benefit
3a. This requires creating a utility function for the agents and their goals. I think we can have a baseline utility function that just sums up a few different factors (popularity, ideology, interest group appeal), and then when generating the agents we randomly sample coefficients for that utility function
3b. We need negative consequences for more actions

# Other notes:
- If a politician fails to achieve office, we should rank them down in the simulation level and then do something about the office: either select an inactive politician from the region to pick up the office or generate a new agent to fill in the office
- If a legislative vote ties, the executive should have the tie-breaker