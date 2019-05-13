from evalg.authentication import user


def test_mock_user_is_authenticated(db_session, logged_in_user, config):
    # Primarily tests the logged in user fixture
    assert user.person
    mock_login_as = config.FEIDE_MOCK_LOGIN_AS
    mock_user = config.FEIDE_MOCK_DATA['users'].get(mock_login_as)
    assert user.dp_user_id == mock_user['id']
