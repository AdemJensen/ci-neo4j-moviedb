'use client'
import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function TMDBAuthPage() {
  const searchParams = useSearchParams()
  const router = useRouter()

  useEffect(() => {
    const request_token = searchParams.get('request_token')
    if (request_token) {
      fetch(`http://localhost:10000/tmdb/create-session?request_token=${request_token}`)
        .then(res => res.json())
        .then(({ session_id }) => {
          localStorage.setItem('tmdb_session_id', session_id)
          return fetch(`http://localhost:10000/tmdb/account?session_id=${session_id}`)
        })
        .then(res => res.json())
        .then(user => {
          localStorage.setItem('tmdb_user', JSON.stringify(user))
          router.push('/')
        })
    }
  }, [searchParams, router])

  return <p>Logging you in...</p>
}
