import ibm_db
import ibm_db_dbi

chepd = {
    'name': 'sheprd',
    'host': 'sheprd',
    'port': '9000',
    'user': 'm57311',
    'password': 'admin123' }

defaultdb = chepd

def  OpenDB(pdict=defaultdb, password=None, **params):
    """
    This function will attempt to create an IBM_DB_DBI connection.
    You may pass it a dictionary of values or named parameter values.
    The values it needs are: name, host, port, user, and password.
    It will user the values from defaultdb by default.

    Example1:
        mydb = {
            'name': 'sheprd',
            'host': 'sheprd',
            'port': '9000',
            'user': 'm57311',
            'password': 'admin123' }
        connection = OpenDB(mydb)

    Example2:
        connection = OpenDB(
            name = 'sheprd',
            host = 'sheprd',
            port = 9000,
            user = 'me',
            password = '1234' )

    Values from named parameters will override those in the dictionary
    The unnamed second parameter can be a password that overides other values

    Example3:
        mydb = {
            'name': 'sheprd',
            'host': 'sheprd',
            'port': '9000',
            'user': 'm57311',
            'password': 'old_password'}
        connection = OpenDB(
            mydb,
            'new password', # this password will be used
            password='what?', # this password would be used if not for above line
            host = 9001 )
    """


    plist = []
    for param in ('name', 'host', 'port', 'user', 'password'):
        v = params.get(param, None) or pdict.get(param, None)
        if param == 'password':
            v = password or v or params.get('pw', None)
        assert v, 'OpenDB Error: {} not given'.format(param)
        plist.append(v)

    connstr = "DATABASE={};HOSTNAME={};PORT={};PROTOCOL=TCPIP;UID={};PWD={};".format(*plist)
    print(connstr)

    try:
        ibmdbconn = ibm_db.connect(connstr, '', '')
        conn = ibm_db_dbi.Connection(ibmdbconn)
    except:
        print('OpenDB failed to open IBM database')
        return False
    return conn

if __name__ == '__main__':
    print('testing OpenDB function with default values')
    conn = OpenDB()
    assert conn, "OpenDB test failed"
