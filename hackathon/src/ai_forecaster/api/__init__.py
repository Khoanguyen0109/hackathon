"""FastAPI surface that mirrors the AI deployment-chart user flow.

Screens (see ``examples/ai_deployment_chart_userflow.html``) map to routers:

========================  ===========================================
Screen                    Router                 Prefix
========================  ===========================================
0 Store profile           routers.stores         /api/v1/stores, /stations, /tasks
1 Crew setup              routers.crew           /api/v1/stores/{id}/crew
2 AI suggestion — context routers.context        /api/v1/context
2 AI suggestion — grid    routers.forecast       /api/v1/forecast
3 Deployment chart        routers.deployments    /api/v1/deployments
4 Summary                 routers.deployments    /api/v1/deployments/{id}/summary
5 Saved charts            routers.deployments    /api/v1/deployments
ops (health, info)        routers.ops            /health, /api/v1/info
========================  ===========================================
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
