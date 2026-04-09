## ALWAYS REMINDER: FOCUS ON CLEAN, CONCISE, READABLE CODE. WE DO NOT CARE ABOUT BACKWARDS COMPATABILITY OR EXCESSIVE FALLBACKS

# Issues of note:
## Elections 
Elections are pretty static since we're always talking about the same agents coming in and out. Right now, if one of the five councilors becomes mayor, then we have a four person council. This is an issue
- We need term limits, set the default as 2 consective terms for executive and 4 consecutive for legislative
- Not all councilmen should run for mayor, there should be a legitimate decision here where:
    1. Nominations happen through the party
    2. The party can only nominate one individual
    3. Nominations should happen through a balance of who is the most popular individual, who has the highest party standing, and who has the best relationship with the party leadership
    4. There should be a cost to running, such that a party can decide to not run in some races to focus in other races (or invest more in some races and less in others)
- For legislative elections, parties can nominate as many candidates as there are seats. If they wish to nominate more candidates than there are agents, they can simply generate new agents
- If an interest group is split up over many candidates or many parties, then it should be able to offer less support to candidates
- We need to create a system, which can be hacky for now, for deleting agents which are not really relevant 

## Parties
- We need to make party directives more clear. Whenever a policy is generated, there should be a quantity of party support for it, (e.g. float from -1 to 1) and each party should have an acceptability threshold, which we use as a parameter in an equation to determine party pushback for breaking with directives
    - an easy implementation would be: pushback = min(party_support + threshold, 0)
    - we then use this pushback metric to modify party standing of an individual
- We should also simulate party elections, such that agents in a party can vote for a new leader
    - They should balance personal relationship, member popularity, high office position, and ideological alignment between themselves and the candidate
    - Party leader should then assign whips, getting a relationship and party standing boost for the whips. This calculation should also take in multiple factors
- If a member gets kicked out from a party, they have to find another party. For now, a hacky solution could just be to auto-assign them to another party and throw something in the logs. You should lose popularity amongst the interest groups of the party you were kicked from, and gain some on the interest groups opposed to that party. Loss should be greater than the gain.
- A representative should be afraid of getting kicked from a party if they don't have other parties ideologically similar to them, or if they are not popular enough to get elected without support of their current party. This should be part of the voting consideration: assess a risk of getting kicked out of a party

## Smaller notes
- Build relationship logs should be a bit more verbose, I want to know 'with who'
- Similarly, logs should include an agent id alongside their name in case of repeated names
- Agents get stuck abstaining instead of voting 'No'. Lets have it so that abstaining only occurs explicitly if a voter wants to vote no, but the party directive is to vote 'Yes'