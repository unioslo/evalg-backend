

queries = {
    'masterKeys': """
    query {
      masterKeys{
        id
        description
        publicKey
        active
        createdAt
      }
    }
    """,
    'electionList': """
    query($id: UUID!) {
      electionList(id: $id) {
        id
        name
        description
        informationUrl
        electionId
        election {
          id
        }
        candidates {
          id
        }
      }
    }
    """,
    'candidate': """
    query($id: UUID!) {
      candidate(id: $id) {
        id
        listId
        name
        meta
        informationUrl
        priority
        preCumulated
        userCumulated
        list {
          id
        }
      }
    }
    """,
    'votesForPerson': """
    query($id: UUID!) {
      votesForPerson(id: $id) {
        voterId
        ballotId
        voter {
          id
        }
      }
    }
    """,
    'person': """
    query($id: UUID!) {
      person(id: $id) {
        id
        email
        displayName
        lastUpdate
        lastUpdateFromFeide
        principal {
          id
          personId
        }
        identifiers {
          personId
          idType
          idValue
        }
      }
    }
    """,
    'personForVoter': """
    query($voterId: UUID!) {
      personForVoter(voterId: $voterId) {
        id
        email
        displayName
        lastUpdate
        lastUpdateFromFeide
        principal {
          id
          personId
        }
        identifiers {
          personId
          idType
          idValue
        }
      }
    }
    """,
    'viewer': """
    query {
      viewer {
        person {
          id
          email
          displayName
          lastUpdate
          lastUpdateFromFeide
          principal {
            id
            personId
          }
          identifiers {
            personId
            idType
            idValue
          }
        }
      }
    }
    """,
    'electionTemplate': """
    query {
      electionTemplate
    }
    """,
    'electionGroup': """
    query($id: UUID!) {
      electionGroup(id: $id) {
        id
        name
        description
        meta
        ouId
        publicKey
        announcedAt
        publishedAt
        cancelledAt
        deletedAt
        templateName
        type
        published
        status
        cancelled
        deleted
        announced
        latestElectionGroupCount {
          id
        }
        elections {
          id
        }
        electionGroupCounts {
          id
        }
        publicationBlockers
      }
    }
    """,
    'electionGroupKeyMeta': """
    query($id: UUID!) {
      electionGroupKeyMeta(id: $id) {
        generatedAt
        generatedBy {
          id
          email
          displayName
          lastUpdate
          lastUpdateFromFeide
          principal {
            id
            personId
          }
          identifiers {
            personId
            idType
            idValue
          }
        }
      }
    }
    """,
    'votersForPerson': """
    query($id: UUID!) {
      votersForPerson(id: $id) {
        id
        idType
        idValue
      }
    }
    """,
    'electionGroupCountingResults': """
    query($id: UUID!) {
      electionGroupCountingResults(id: $id) {
        id
        groupId
        initiatedAt
        finishedAt
        status
      }
    }
    """,
    'electionGroupCount': """
    query($id: UUID!) {
      electionGroupCount(id: $id) {
        id
        groupId
        initiatedAt
        finishedAt
        status
      }
    }
    """,
    'searchVoters': """
    query(
        $electionGroupId: UUID!,
        $selfAdded: Boolean,
        $reviewed: Boolean,
        $verified: Boolean,
        $hasVoted: Boolean,
        $limit: Int,
        $search: String,
        $pollbookId: UUID,
    ) {
      searchVoters(
        electionGroupId: $electionGroupId,
        selfAdded: $selfAdded,
        reviewed: $reviewed,
        verified: $verified,
        hasVoted: $hasVoted,
        limit: $limit,
        search: $search,
        pollbookId: $pollbookId,
      ) {
        id
        idType
        idValue
      }
    }
    """,
    'electionResult': """
    query($id: UUID!) {
      electionResult(id: $id) {
        electionProtocol
        ballots
        id
        electionId
        electionGroupCountId
        result
        pollbookStats
        ballotsWithMetadata
      }
    }
    """,
}
