from flask import render_template, redirect


def register_admin_routes(app, deps):
    """Admin routes migrated from app.py.

    V1.06 Bloco 1.4A:
    - /admin
    - /admin/users
    - /admin/system
    - /admin/feedback
    - /admin/invites

    POST actions stay in app.py for now.
    """

    admin_required_redirect = deps["admin_required_redirect"]
    current_user = deps["current_user"]

    User = deps["User"]
    SystemLog = deps.get("SystemLog")
    FeedbackReport = deps.get("FeedbackReport")
    BetaInvite = deps.get("BetaInvite")
    MatchHistory = deps.get("MatchHistory")

    is_smtp_configured = deps.get("is_smtp_configured")
    dev_tools_enabled = deps.get("dev_tools_enabled")

    @app.route("/admin", endpoint="admin")
    def admin_route():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        total_users = 0
        verified_users = 0
        total_matches = 0
        open_feedbacks = 0

        try:
            total_users = User.query.count()
            verified_users = User.query.filter_by(is_verified=True).count()
        except Exception as error:
            print("Admin user stats failed:", type(error).__name__, error)

        try:
            if MatchHistory:
                total_matches = MatchHistory.query.count()
        except Exception as error:
            print("Admin match stats failed:", type(error).__name__, error)

        try:
            if FeedbackReport:
                open_feedbacks = FeedbackReport.query.filter_by(status="open").count()
        except Exception as error:
            print("Admin feedback stats failed:", type(error).__name__, error)

        return render_template(
            "admin.html",
            user=current_user(),
            total_users=total_users,
            verified_users=verified_users,
            total_matches=total_matches,
            open_feedbacks=open_feedbacks,
            dev_tools_enabled=dev_tools_enabled() if dev_tools_enabled else False,
        )

    @app.route("/admin/users", endpoint="admin_users")
    def admin_users_route():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        users = []

        try:
            users = User.query.order_by(User.id.desc()).limit(500).all()
        except Exception as error:
            print("Admin users query failed:", type(error).__name__, error)

        return render_template("admin_users.html", user=current_user(), users=users)

    @app.route("/admin/system", endpoint="admin_system")
    def admin_system_route():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        logs = []

        try:
            if SystemLog:
                logs = SystemLog.query.order_by(SystemLog.id.desc()).limit(100).all()
        except Exception as error:
            print("Admin system logs query failed:", type(error).__name__, error)

        return render_template(
            "admin_system.html",
            user=current_user(),
            logs=logs,
            smtp_configured=is_smtp_configured() if is_smtp_configured else False,
            dev_tools_enabled=dev_tools_enabled() if dev_tools_enabled else False,
        )

    @app.route("/admin/feedback", endpoint="admin_feedback")
    def admin_feedback_route():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        feedbacks = []

        try:
            if FeedbackReport:
                feedbacks = FeedbackReport.query.order_by(FeedbackReport.id.desc()).limit(200).all()
        except Exception as error:
            print("Admin feedback query failed:", type(error).__name__, error)

        return render_template("admin_feedback.html", user=current_user(), feedbacks=feedbacks)

    @app.route("/admin/invites", endpoint="admin_invites")
    def admin_invites_route():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        invites = []

        try:
            if BetaInvite:
                invites = BetaInvite.query.order_by(BetaInvite.id.desc()).limit(200).all()
        except Exception as error:
            print("Admin invites query failed:", type(error).__name__, error)

        return render_template("admin_invites.html", user=current_user(), invites=invites)
