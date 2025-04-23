"use client";

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {usePathname} from "next/navigation";
import {gotoAuthPage} from "@/lib/utils";

export default function Navbar() {
  const [user, setUser] = useState(null)
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    const stored = localStorage.getItem('tmdb_user')
    if (stored) {
      setUser(JSON.parse(stored))
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('tmdb_user')
    localStorage.removeItem('tmdb_session_id')
    setUser(null)
    setOpen(false)
    window.location.reload()
  }

  const avatarUrl = user?.avatar?.tmdb?.avatar_path
    ? `https://www.themoviedb.org/t/p/w64_and_h64_face${user.avatar.tmdb.avatar_path}`
    : `https://www.gravatar.com/avatar/${user?.avatar?.gravatar?.hash}?s=64`

  const tabs = [
    { name: 'Recommendations', href: '/recommendations', alias: '/form-recommendation' },
    { name: 'Actors', href: '/actors' },
    { name: 'Movies', href: '/movies' },
  ]

  return (
    <nav className="bg-gray-900 text-white flex items-center justify-between px-6 py-4 shadow-md">
      {/* Left: Brand */}
      <div className="text-2xl font-semibold tracking-wide text-yellow-400">
        <Link href="/">MovieDB</Link>
      </div>

      {/* Center: Tabs */}
      <div className="hidden md:flex gap-6 text-sm font-medium">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={`hover:text-yellow-300 transition ${
              pathname === tab.href || pathname === tab.alias ? 'text-yellow-400 border-b-2 border-yellow-400 pb-1' : 'text-white'
            }`}
          >
            {tab.name}
          </Link>
        ))}
      </div>

      {/* Right: User Avatar or Login */}
      <div className="relative">
        {!user ? (
          <button
            onClick={gotoAuthPage}
            className="bg-yellow-400 hover:bg-yellow-500 text-black font-medium px-4 py-2 rounded-full transition"
          >
            Login via TMDB
          </button>
        ) : (
          <div className="relative">
            <img
              src={avatarUrl}
              alt="Avatar"
              className="w-10 h-10 rounded-full cursor-pointer ring-2 ring-yellow-300"
              onClick={() => setOpen(!open)}
            />
            {open && (
                <div className="absolute right-0 mt-2 w-48 bg-white text-black rounded-lg shadow-lg z-50 text-center">
                  <div className="px-4 py-2 border-b text-sm font-semibold">
                    {user.name || 'Unnamed'}
                  </div>
                  <button
                      className="w-full px-4 py-2 text-sm hover:bg-gray-100"
                  >
                    <Link href="/favorites">Favorites</Link>
                  </button>
                  <button
                      onClick={handleLogout}
                      className="w-full text-red-700 px-4 py-2 text-sm hover:bg-gray-100"
                  >
                    Logout
                  </button>
                </div>
            )}
          </div>
        )}
      </div>
    </nav>
  )
}

export {Navbar}