from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClass()

class Actions(ActionsBase):

    """
    """


    def configure(self, service):
        import requests
        import urllib
        name = service.hrd.get('instance.ovc.environment')
        secret = service.hrd.get('instance.itsyouonline.secret')
        clientid = service.hrd.get('instance.itsyouonline.client_id')
        orgname = service.hrd.get('instance.itsyouonline.orgname')
        baseurl = "https://itsyou.online"
        params = {'grant_type': 'client_credentials',
                  'client_id': clientid,
                  'client_secret': secret}
        accesstokenurl = "%s/v1/oauth/access_token?%s" % (baseurl, urllib.urlencode(params))
        session = requests.Session()
        tokenresp = session.post(accesstokenurl)
        if not tokenresp.ok:
            raise RuntimeError('Failed to get access token')
        token = tokenresp.json()
        print token
        accesstoken = token['access_token']
        #accesstoken = 'Bok2h8ikZ1x66_W6oGbqhgRS3GtQ'
        session.headers['Authorization'] = 'token %s' % accesstoken
        session.headers['Content-Type'] = 'application/json'

        mainorg = session.get('%s/api/organizations/%s' % (baseurl, orgname)).json()
        locationorgname = '%s.%s' % (orgname, name)
        locationorg = {'members': [],
                       'publicKeys': [],
                       'owners': [],
                       'globalid': locationorgname,
                       'dns': []}
        url = '%s/api/organizations/%s' % (baseurl, locationorgname)
        resp = session.post(url, data=locationorg)
        print url, locationorg
        print resp, resp.text

