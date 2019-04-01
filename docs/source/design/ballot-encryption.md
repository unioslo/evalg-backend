# Kryptering av stemmesedler

Vi har tidligere kommet frem til at kryptering på backend er beste løsningen.  
Hvis krypteringen skjer på frontend har vi ingen mulighet til å verifisere at 
stemmen er gyldig og feilfri før ved opptelling. 

## Flyt for kryptering av stemmesedler 
Nøkkelpar blir generert av frontent ved opprettelse av valget. Den offentlige
nøkkelen ble da lagret i backend. Den private nøkkelen lagres lokalt av
valgadmin.    

1. Bruker avgir en stemme i et valg, og en stemmeseddel blir generert. 
2. Stemmeseddel overføres ukryptert til backend. Transport er kryptert med ssl.
3. Validering av stemmeseddel og innhold. (Finnes kandidatene i valget osv).
4. Generer og lagre en kryptografisk hash av stemmeseddelen.
5. Stemmeseddelen paddes.
6. Backend henter fram den riktig offentlig nøkkel for valget.
7. Stemmeseddelen krypteres med valgets offentlige nøkkel. 
8. Den krypterte stemmeseddelen lagres i databasen. 
9. Backend kvitterer tilbake til frontend. 

``` seqdiag:: election-flow.diag
```



## Generelle prinsipper
- Kryptering basert på NaCl (Curve25519)
- Krypteringen skjer på backend.
- Stemmeseddelen skal aldri lagres ukryptert. En bør begrense tiden
stemmeseddelen er i minne på maskinen.
- Valgets offentlige nøkkelen brukes til kryptering.
- Bytte av offentlig nøkkel etter at det er avgitt stemmer i et valg støttes 
ikke (rekryptering).


### Integritet og verifisering (hashing)
En kryptert stemmeseddel kan saboteres ved at en eller flere bytes endres på.
Vi må fange opp at noe slikt har skjedd ved dekryptering og ikke ved at vi får
data med feil ut.

Pynacl ser ut til å ordne noe av dette selv. I test kom feilmeldingen 
«CryptoError: An error occurred trying to decrypt the message» opp etter endring av en byte.

For å sikre at en dekrypterte stemme er korrekt kan det genereres opp en kryptografisk hash i forkant av krypteringen.
Dennne kan brukes til å verifiseres stemmeseddelen etter dekryptering.
[PyNaCl har støtter for flere slike](https://pynacl.readthedocs.io/en/stable/hashing/)


Generering av blake2b hash:
```python
import nacl.encoding
import nacl.hash

HASHER = nacl.hash.blake2b
ballot = json.dumps('{"vote_for": "Einar Gerhardsen"}', ensure_ascii=False).encode('utf-8')
ballot_hash = HASHER(ballot, encoder=nacl.encoding.Base64Encoder)
```

Systemet kan evt. også signere stemmesedlene med en egen nøkkel ved kryptering. 
En kan da verifisere at stemmen er kryptert av systemet.
```python
from nacl.public import Box

sealed_box = Box(system_private_key, election_public_key)
```


### Padding
NaCl skuler ikke lengden på den krypterte meldingen. Dette muliggjør at
informasjon om stemmegivningen kan avsløres med statisk analyse av de
krypterte stemmesedlene. For å unngå dette må stemmesedlene paddes slik at
alle stemmer i et valg har samme lengde. Paddingen må være stor nok til å kunne dekke alle
mulige stemmesedler i et valg.


### Nonce
PyNaCl generer opp tilfeldig nonce automatisk.

## Se på/advanced 
Som en del av å implementere kryptering av stemmesedler bør en se på følgende:

- Vurder å bytte ut NaCl pakken i frontend fra js-nacl til tweetnacl.
Sistnevnte har en vesentlig mye større brukermasse (500 vs 8500000).
- Vurder om stemmer bør signeres med en egen system-privatnøkkel. Dette for å
kunne garantere at stemmen er blitt kryptert av systemet.


## Teknisk/implementering 
Python har støtte for NaCl via pakken PyNaCl. Nøkklene kommer som hex
fra frontend.

PyNaCl returnerer kryptert data som binære data, men med muligheten for å velge encoding.
nacl.encoding.Base64Encoder brukes i eksemplene under. Kryptert data er da en base64 bytestring.


```python
from nacl.public import PrivateKey, PublicKey
public = '592484f031a7ac4fae8bb0bc113149300220e993e4bb33bd7ce6430ee3d9b744'
private = 'c508f716ab74327c9f744f8cfb2419f0c70f2805b3db81ebd71aa1864a4ee266'
pub_key = PublicKey(public_key=public, encoder=nacl.encoding.HexEncoder)
priv_key = PrivateKey(private_key=private, encoder=nacl.encoding.HexEncoder)
```

Siden stemmegiver ikke signerer stemmen, kan vi bruker en SealedBox til
kryptering.

```python
from nacl.public import SealedBox

sealed_box = SealedBox(pub_key)
```

Pynacl støtter bare kryptering av bytes. Stemmedata må konverteres først.

```python
ballot = {"vote_for": "Einar Gerhardsen"}
byte_ballot = json.dumps(ballot, ensure_ascii=False).encode('utf-8')
encrypted_ballot = sealed_box.encrypt(msg, encoder=nacl.encoding.Base64Encoder)
```

Dekryptering og konvertering til string.

```python
unseal_box = SealedBox(priv_key)
decryptet_ballot = unseal_box.decrypt(encrypted, encoder=nacl.encoding.Base64Encoder)
decryptet_ballot = decryptet_ballot.decode('utf-8')

```

