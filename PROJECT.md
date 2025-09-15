# Project 1: Conversation

We'll be simulating a group conversation in which you will be coding players
whose goal is to have a "good" interaction of ideas.  There are some shared properties of
conversations that make them better for all participants. Other properties of
conversations are sought by individual participants. At the end of the conversation,
the whole interaction will be measured according to the collective and individual scoring functions,
which are added together for each participant.  For some conversations, there will be
one or more random players included who may steer the conversation in unpredictable ways.

There are *P* players, and every player has a memory bank of *B* newsworthy items that
they could contribute to the conversation. Half of the items are about a single subject,
while the other half are about two subjects. Every item also has an importance, which is
a number uniformly generated between 0 and 1. There are *S* subjects in total, and each player's
memory bank is generated at random. The conversation has a fixed length *L* that everybody knows in advance.

A conversation is a sequence of items contributed by players. On any turn, each player may propose
to share an item. If multiple players attempt to contribute an item, the simulator will do the following:
If the player currently talking wants to contribute again, they will be chosen with probability 0.5.
If the player currently talking is not chosen, then the simulator will choose a player at random from among
those who propose an item and have so far contributed the smallest number of items among that group.

That way, each player can (if they wish) contribute approximately as often as other players over the long run.
If nobody contributes anything on a given turn, then the sequence is filled by a "pause".
If there are three consecutive pauses, then the conversation ends prematurely.

The shared goals of a conversation are as follows:

- [Coherence] For every item *I*, the (up to) 3 preceding items and (up to) 3 following items are collected into a set *C_I* of context items.
    If a subject of *I* is never mentioned in *C_I* then one point is lost from the final score. If all subjects in *I* are mentioned at least
    twice in *C_I* then one point is added to the final score. The window defining *C_I* does not extend beyond the start of the
    conversation or any pauses.

- [Importance] The total importance of all items in the final item sequence is added to the shared score.

- [Nonrepetition] An item that is repeated has zero importance and does not contribute to the coherence score after the first
    instance of the item.

- [Freshness] Immediately after a pause, an item with a subject that was not previously present in the 5 turns
    prior to the pause gets a point added to the final score. An item with two novel subjects of this sort gets
    two bonus points.

- [Nonmonotonousness] An item with a subject that was also present in each of the previous three items leads to the loss of a point.

Individual goals depend on each player's preferred topics of conversation.
The simulator gives each player a random permutation of the *S* subjects that represents the ranked preference of that player.
An item with a subject that is of rank *k* for that player achieves a bonus of $\frac{1-k}{|S|}$ where *|S|* is the total
number of possible subjects. An item with two subjects gives the player a bonus corresponing to the average of the
two individual bonuses. Players know their own ranking, but not the ranking of other players.

At the end of the game, the total score for each player is divided by
*L*, resulting in an overall conversation quality that is the final metric by which players will be compared.
Even though the shared goals lead to scores for all participants, such scores can still be used to compare players.
For example, how does the global score change when one player is left out? How does the global score vary when all
participants are running the same group's code. Make sure to code your player in an encapsulated fashion, so that several
instances of the same player can be instatiated without sharing information across instances.
We'll run a variety of configurations for various combinations of parameters as part of a tournament at the end of the project.
The precise configurations for the tournament will be discussed in class. The simulator will accept a random number
seed to facilitate repeatable simulations.

Your primary goal is to code a player that achieves the highest conversation quality. Additionally, I would like to see some
analysis of the resulting conversations. For example, how do long conversations compare to short ones? Are there emergent patterns
in the conversations? How badly do one (or more) random players affect a conversation's quality?
