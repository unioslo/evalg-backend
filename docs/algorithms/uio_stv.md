## Main algorithm:

uio\_stv implements a standard [single transferable vote](https://en.wikipedia.org/wiki/Single_transferable_vote).

TODO: more info on how the algorithm actually is implemented

## Quota rules:

uio_stv only supports having 2 quota groups.
By default the quota rules will be applied seperately to the regular candidates and the substitute candidates.

If 1 person is to be elected no rules are applied.
If 2 or 3 people are to be elected, at least 1 from each group will be elected.
For more than 3 people 40%, rounded up, will be elected.

If oslomet\_quotas is set to true the quotas will be shared in the case where only one regular and one substitute is to be elected. Ensuring they are from different quota groups.
