"use client";

import {Suspense, useEffect} from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {apiService} from "@/lib/api-config";

function TMDBAuth() {
  const searchParams = useSearchParams()
  const router = useRouter()

  useEffect(() => {
    const request_token = searchParams.get('request_token')
    if (request_token) {
      apiService.fetchData(`/tmdb/create-session?request_token=${request_token}`)
        .then(res => res.json())
        .then(({ session_id }) => {
          localStorage.setItem('tmdb_session_id', session_id)
          return apiService.fetchData(`/tmdb/account?session_id=${session_id}`)
        })
        .then(res => res.json())
        .then(user => {
          localStorage.setItem('tmdb_user', JSON.stringify(user))
          router.push('/')
        })
    }
  }, [searchParams, router])

  return (
      <p>Logging you in...</p>
  )
}

export default function TMDBAuthPage() {
    return <Suspense fallback={<p>Loading TMDB login...</p>}>
        <TMDBAuth/>
      </Suspense>
}
