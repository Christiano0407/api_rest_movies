"""
  === TMDB | Vinculación de cuenta real de TMDB (requerido por /account/watchlist) ===
"""

from __future__ import annotations









## ---- request token ----- ##
""" @router.post("/tmdb/request-token", response_model=TMDBRequestTokenResponse)
async def create_tmdb_request_token(
    user: Users = Depends(get_current_user)
    ) -> TMDBRequestTokenResponse: 
    request_tokens = await create_tokens()
    authorization_urls = f"https://www.themoviedb.org/authenticate/{request_tokens}"
    return TMDBRequestTokenResponse(
        request_token=request_tokens, 
        tmdb_authorize_url=authorization_urls
    ) """