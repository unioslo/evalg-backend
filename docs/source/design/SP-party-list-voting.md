# JSON-Format:
```
{
    "voteType": "SPListElecVote",
    "chosenListId": "listId",
    "personalVotesOtherParty":
    [
        {
            "person": "personId",
            "list": "listId"
        }
    ]
    "personalVotesSameParty":
    [
        "personId"
    ]
}
```

## Hovedtanke

Man velger en liste, for så å gjøre kumuleringer på kandidater i den lista og legge til slengere fra andre lister.

## Kumulering

Kumulering finnes i to varianter, forhåndskumulering og vanlig kumulering gjort av den som stemmer.
Forhåndskumulering vil være definert i lista man velger, og er ikke noe personen som stemmer kan endre på.
Når man kumulerer vil det være tilsvarende å gi en personstemme og derfor være synlig i stemmeseddelen i
attributtet "personalVotesSameParty"

## Stryking

Stryking ser ikke ut til å være mulig, men har sendt mail for å være sikker. I så fall må nok et ekstra felt til.

## Føre opp kandidater fra andre lister

Personstemmer til kandidater fra andre lister, såkalte slengere, vil være tilgjengelig i "personalVotesOtherParty".

## Tekniske begrensninger etter stemming er påbegynt

Ettersom en stemme er knyttet mot en liste vil det være problematisk å endre lista senere.
Det gjør at en person sin stemme blir endret etter den er avlagt.
Valgreglementet til Studentparlamentet sier at valglister skal være inne på forhånd.
Dette bør ikke være et realistisk ønske. 
Hvis man har gjort feil i valget og stemming er påbegynt bør valget startes på nytt.
