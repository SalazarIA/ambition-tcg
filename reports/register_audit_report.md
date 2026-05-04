
## Compile check

OK: app.py/models.py compile

## Register route source

```python
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        invite_code = request.form.get("invite_code", "").strip().upper()

        if not username or not email or not password:
            flash("Fill all fields.")
            return redirect("/register")

        if len(password) < 6:
            flash("Password must have at least 6 characters.")
            return redirect("/register")

        invite = None

        if app.config.get("BETA_INVITE_REQUIRED"):
            if not invite_code:
                flash("Beta invite code is required.")
                return redirect("/register")

            invite = BetaInvite.query.filter_by(code=invite_code).first()

            if not invite or not invite.can_be_used():
                flash("Invalid or expired invite code.")
                return redirect("/register")

        if User.query.filter_by(email=email).first():
            flash("Email already exists.")
            return redirect("/register")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect("/register")

        new_user = User(
            username=username,
            email=email,
            account_status="active",
            is_tester=True if invite else False,
            is_verified=True,
        )
        new_user.set_password(password)

        try:
            new_user.verified_at = datetime.now(timezone.utc)
        except Exception:
            pass

        db.session.add(new_user)

        if invite:
            invite.used_count += 1

        db.session.commit()

        flash("Registered successfully. You can login and play now.")
        log_rc_event(
            "account",
            "User registered without email verification in beta mode",
            user_id=new_user.id,
        )

        return redirect("/login")

    return render_template("register.html")



```

## Suspicious verification leftovers

36: from services.email_service import send_verification_email, send_password_reset_email, send_smtp_test_email, is_smtp_configured
192:     if getattr(user, "account_status", "active") in ["banned", "disabled"]:
199:     user.is_verified = True
200:     user.account_status = "active"
574:     if not bool(getattr(user, "is_verified", False)):
576:         return redirect("/resend-verification")
578:     if getattr(user, "account_status", "active") in ["banned", "disabled"]:
604:         "is_verified": bool(user.is_verified),
606:         "account_status": getattr(user, "account_status", None),
782:         verified_users=User.query.filter_by(is_verified=True).count(),
892:         target.account_status = "banned"
915:         target.account_status = "active" if target.is_verified else "unverified"
1135:         verified_users = User.query.filter_by(is_verified=True).count()
1273: @app.route("/resend-verification", methods=["GET", "POST"])
1282:             return redirect("/resend-verification")
1284:         if user.is_verified:
1291:         sent = send_verification_email(user, verification_url)
1500:         "status": getattr(user, "account_status", "beta"),
1502:         "is_verified": bool(getattr(user, "is_verified", False)),
1830:             account_status="active",
1832:             is_verified=True,
1861: @app.route("/confirm_email/<token>")
1862: def confirm_email(token):
3609:         verified_users = User.query.filter_by(is_verified=True).count()

## Flask test client GET/POST register

GET /register: 200 location=None
POST /register: 400 location=None
Response preview:
```html
<!doctype html>
<html lang=en>
<title>400 Bad Request</title>
<h1>Bad Request</h1>
<p>Invalid CSRF token.</p>

```
USER NOT CREATED

## Recent git diff around app.py

```diff
diff --git a/app.py b/app.py
index 40fd635..13c5dc9 100644
--- a/app.py
+++ b/app.py
@@ -1829,21 +1829,20 @@ def register():
             email=email,
             account_status="active",
             is_tester=True if invite else False,
+            is_verified=True,
         )
         new_user.set_password(password)
 
-        db.session.add(new_user)
-
-        if invite:
-            invite.used_count += 1
-
-        new_user.is_verified = True
-        new_user.account_status = "active"
         try:
             new_user.verified_at = datetime.now(timezone.utc)
         except Exception:
             pass
 
+        db.session.add(new_user)
+
+        if invite:
+            invite.used_count += 1
+
         db.session.commit()
 
         flash("Registered successfully. You can login and play now.")
@@ -1858,6 +1857,7 @@ def register():
     return render_template("register.html")
 
 
+
 @app.route("/confirm_email/<token>")
 def confirm_email(token):
     try:


```