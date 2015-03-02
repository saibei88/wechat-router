import tornado.auth
import tornado.web
from tornado import gen
import urlparse
from tornado.auth import AuthError

class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user_json = self.get_secure_cookie("chatdemo_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("chatdemo_user")
        self.write("You are now logged out")

class NtseMixin(tornado.auth.OpenIdMixin):
    _OPENID_ENDPOINT = "https://login.netease.com/openid"

    def _openid_args(self, callback_uri, ax_attrs=[], oauth_scope=None):
        url = urlparse.urljoin(self.request.full_url(), callback_uri)
        args = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.identity":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.return_to": url,
            "openid.realm": urlparse.urljoin(url, '/'),
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update({
                "openid.ns.sreg": "http://openid.net/extensions/sreg/1.1",
                "openid.ax.mode": "fetch_request",
            })
            ax_attrs = set(ax_attrs)
            required = []
            if "name" in ax_attrs:
#                ax_attrs -= set(["fullname", "nickname"])
                required += ["fullname", "nickname","email"]
            args["openid.sreg.required"] = ",".join(required)
            
        if oauth_scope:
            args.update({
                "openid.ns.oauth":
                "http://specs.openid.net/extensions/oauth/1.0",
                "openid.oauth.consumer": self.request.host.split(":")[0],
                "openid.oauth.scope": oauth_scope,
            })
        return args

    def _on_authentication_verified(self, future, response):
        if response.error or b"is_valid:true" not in response.body:
            future.set_exception(AuthError(
                "Invalid OpenID response: %s" % (response.error or
                                                 response.body)))
            return

        # Make sure we got back at least an email from attribute exchange
        ax_ns = None
        for name in self.request.arguments:
            if name.startswith("openid.ns.") and \
                    self.get_argument(name) == u"http://openid.net/srv/ax/1.0":
                ax_ns = name[10:]
                break

        def get_ax_arg(uri):
            if not ax_ns:
                return u("")
            prefix = "openid." + ax_ns + ".type."
            ax_name = None
            for name in self.request.arguments.keys():
                if self.get_argument(name) == uri and name.startswith(prefix):
                    part = name[len(prefix):]
                    ax_name = "openid." + ax_ns + ".value." + part
                    break
            if not ax_name:
                return u("")
            return self.get_argument(ax_name, u(""))

        email = self.request.arguments.get("openid.sreg.email",None)
        fullname = self.request.arguments.get("openid.sreg.fullname",None)
        nickname = self.request.arguments.get("openid.sreg.nickname",None)
        user = dict()
        name_parts = []
        if email:
            user["email"] = email[0]
        if fullname:
            user["fullname"] = fullname[0]
        if nickname:
            user["nickname"] = nickname[0]
        claimed_id = self.get_argument("openid.claimed_id", None)
        if claimed_id:
            user["claimed_id"] = claimed_id
        future.set_result(user)
        
class AuthLoginHandler(BaseHandler, NtseMixin):

    @gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user()
            self.set_secure_cookie("chatdemo_user",
                                   tornado.escape.json_encode(user.get("email")))
            self.redirect("/")
            return
        self.authenticate_redirect(ax_attrs=["name"])
