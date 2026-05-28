import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth.auth_manager import AuthManager

am = AuthManager()
ok, msg = am.signup('devtester', 'devtester@example.com', 'DevPass123', 'DevPass123')
print('ok=', ok)
print('msg=', msg)
