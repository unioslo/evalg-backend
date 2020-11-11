# JSON-Format:
```
{
    "personstemmer":
    [
        "personId"
    ]
}
```

# Hvordan håndterer dette alt?

## Hovedtanke

I dag er hvilken liste man velger egentlig helt uviktig for stemmeseddelen. 
Det eneste man ser på i opptellingen er personstemmene som gis.
Derfor holder det at stemmeseddelene inneholder hvilke personer man ønsker å stemme på.

Når man velger en valgliste fylles stemmeseddelen ut slik som valglista ser ut.
Ønsker man å gjøre endringer er det bare å endre på denne lista. 

## Kumulering

Kumulering tilsvarer at en person dukker opp en ekstra gang i listen over personstemmer.
Hvis du stemmer på 3 personer P1, P2 og P3, i denne rekkefølgen med kumulering på P1 og P2
vil stemmeseddelen se slik ut:
```
{
    "personstemmer":
    [
        "P1_id",
        "P1_id",
        "P2_id",
        "P2_id",
        "P3_id"
    ]
}
```

## Stryking

Stryking gjøres enkelt ved at man bare fjernes en person fra listen over personstemmer man vil gi.

## Føre opp kandidater fra andre lister

Dette er også enkelt med denne modellen ettersom det ikke er noen tilknytting til liste i stemmeseddelen.
Det er altså bare å legge til en person fra en annen valgliste i stemmeseddelen

# Tekniske begrensninger etter stemming er påbegynt

Personer som er stemt på må finnes, hvis ikke vil det være problemer med å koble stemmene mot personer 
i opptellinga. Ellers er det ingen tekniske hindringer mot å endre på f.eks lister
etter at valget er startet. Men man kan argumentere for at det er noen demokratiske problemer ved dette.
