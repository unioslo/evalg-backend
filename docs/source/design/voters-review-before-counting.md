# Gjennomgang av voters før opptelling

\* = Implementere i resistanssak EVALG-469.

## GraphQL-API

### Fields

#### Voter.status: VoterStatus

En voter har en av disse statusene.

| Status                     | Forklaring |
|----------------------------|------------|
| ADMIN_ADDED_AUTO_VERIFIED  | Admin har lagt til voter gjennom manntall-siden, ingen annen behandling gjort.
| ADMIN_ADDED_REJECTED       | Admin har lagt til voter gjennom manntall-siden, person for voter har flere verified voters som har hver sin vote innenfor election-group'en, og denne voter er avvist i flere-stemmer-for-person-behandling.
| SELF_ADDED_NOT_REVIEWED    | En voter opprettet i det en person har stemt der personen ikke hadde en ADMIN_ADDED_AUTO_VERIFIED voter i den aktuelle pollbook.
| SELF_ADDED_VERIFIED        | En tidligere SELF_ADDED_NOT_REVIEWED voter som er godkjent av admin i stemmer-utenfor-manntall-behhandling (admin har vurdert at tilknyttet person har stemmrett i manntallet).
| SELF_ADDED_REJECTED        | Enten en tidligere SELF_ADDED_NOT_REVIEWED voter som er avvist av admin i utenfor-manntall-behandling (admin har vurdert at tilknyttet person ikke har stemmerett i manntallet), eller en tidligere SELF_ADDED_VERIFIED voter der person for voter har flere verified voters med hver sin vote innenfor election-group'en, der denne voter er avvist i flere-stemmer-for-person-behandling. I begge tilfeller vises voteren i listen over avviste voters i stemmer-utenfor-manntall-behandling.

Kommentarer:
- Av disse fem har en ADMIN_ADDED_AUTO_VERIFIED voter ikke nødvendigvis en tilknyttet vote, mens de andre typene voter skal nødvendigvis ha en tilknyttet vote.
- Votes tilknyttet begge typene verified voters skal telle under opptelling.
- *Når opptelling forøkes startes må backend verifisere at samme person ikke er knyttet til mer enn en verified voter innenfor hele election_group'en. (Frontend bør heller ikke gi noen mulighet for å starte opptelling før flere-stemmer-for-person-behandling-listen er tom.)

#### ElectionGroup.personsWithMultipleVotes: Person[] *

Returnerer personer som er knyttet til flere verified voters med stemmer.

For å implementere flere-stemmer-for-person-behandling bør et slikt kall/felt være tilgjengelig. For å implementere resolveren kan man i Voter-tabellen, hvis det ikke er det, ha en kolonne for Person som populeres når en Voter avgir en stemme. Så kan man gå gjennom alle Voters i election-group'en og se om noen har samme Person, og returnere de personene som har flere voters __med stemme__. Så kan frontend benytte votersForPerson-querien og filtere på election-group'ens pollbooks for å vise frem hvilke manntall personene har stemt i.

### Mutations

#### reviewSelfAddedVoter(voterId: UUID!, verify: Boolean!)

Setter en SELF_ADDED_NOT_REVIEWED voter til SELF_ADDED_VERIFIED (verify: true) eller SELF_ADDED_REJECTED (verify: false).

#### undoReviewSelfAddedVoter(voterId: UUID!)

Setter en voter med status SELF_ADDED_VERIFIED eller SELF_ADDED_REJECTED til SELF_ADDED_NOT_REVIEWED.

#### rejectVoter(voterId: UUID!) *

Setter en ADMIN_ADDED_AUTO_VERIFIED voter til ADMIN_ADDED_REJECTED eller en voter med status SELF_ADDED_VERIFIED til SELF_ADDED_REJECTED.

#### undoRejectAdminAddedVoter(voterId: UUID!) *

Setter en ADMIN_ADDED_REJECTED voter til ADMIN_ADDED_AUTO_VERIFIED.

## UX/UI

### Stemmer-utenfor-manntall-behandling
Denne komponenten vises når alle valg (?) i valggruppen har en av statusene closed/cancelled.

Den består av tre lister:
1. Til behandling - Voters med status SELF_ADDED_NOT_REVIEWED.
2. Godkjente - Voters med status SELF_ADDED_VERIFIED.
3. Avviste - Voters med status SELF_ADDED_REJECTED.

Zeplin-skisser: https://app.zeplin.io/project/589070329fac123a15e487c5/screen/598ae8c00018663d77ede0cb

### Flere-stemmer-for-person-behandling *

Denne komponenten vises i opptelling-seksjoen når stemmer-utenfor-mannall-behandling-listen er tom, og admin har trykket "Kontroller stemmer" eller lignende og det finnes personer som har mer enn en verified voter med stemme innenfor hele election-group'en. Her må admin avvise stemmer inntil samme person kun har en verified voter med stemme innenfor election-group'en.