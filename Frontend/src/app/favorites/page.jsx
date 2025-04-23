'use client'

import {useEffect, useState} from 'react'
import Navbar from '@/components/ui/navbar'
import {Card, CardContent, CardHeader} from '@/components/ui/card'
import {apiService} from "@/lib/api-config";
import Paginator from "@/components/ui/paginator";
import {gotoAuthPage} from "@/lib/utils";
import {useRouter} from "next/navigation";
import RasaChatWidget from "@/components/ui/RasaChatWidget";

export default function FavoritesPage() {
    const router = useRouter();
    const [favorites, setFavorites] = useState([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1);
    const [size] = useState(20); // items per page
    const [total, setTotal] = useState(0);
    const session_id = localStorage.getItem('tmdb_session_id')

    useEffect(() => {
        if (!session_id) {
            gotoAuthPage()
            return
        }

        handlePageChange(1)
    }, [])

    const handlePageChange = (newPage) => {
        setLoading(true)
        setPage(newPage);
        apiService.fetchData(`/tmdb/favorites?session_id=${session_id}&page=${newPage}`)
            .then(res => res.json())
            .then(data => {
                console.log('Favorites data:', data)
                setFavorites(data.results || [])
                setTotal(data.total_results || 0)
                setLoading(false)
            })
            .catch(err => console.error('Error loading favorites', err))
    }

    const handleNavigation = (path) => {
        router.push(path);
    };

    return (
        <div className="min-h-screen bg-gray-100">
            <Navbar/>
            <div className="p-8">
                <Card className="max-w-6xl mx-auto">
                    <CardHeader>
                        <h1 className="text-2xl font-bold">🌟 Favorite Movies</h1>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="flex flex-col justify-center items-center h-96">
                                <p className="text-gray-700 text-lg mb-4">Fetching from TMDB...</p>
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
                            </div>
                        ) : favorites.length === 0 ? (
                            <p className="text-center text-gray-500">No favorites found.</p>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
                                {favorites.map((movie) => (
                                    <Card key={movie.id} className="bg-white shadow hover:shadow-md transition cursor-pointer"
                                        onClick={() => handleNavigation(`/?q=${encodeURIComponent(movie.title)}&type=movie`)}>
                                        <CardContent className="p-3">
                                            {movie.poster_path ? (
                                                <img
                                                    src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
                                                    alt={movie.title}
                                                    className="rounded w-full mb-2"
                                                />
                                            ) : (
                                                <div className="bg-gray-200 h-64 rounded mb-3"/>
                                            )}
                                            <h3 className="text-lg font-semibold">{movie.title}</h3>
                                            <p className="text-sm text-gray-500">{movie.release_date}</p>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                        <Paginator
                            page={page}
                            total={total}
                            size={size}
                            onPageChange={handlePageChange}
                        />
                    </CardContent>
                </Card>
            </div>
            <RasaChatWidget />
        </div>
    )
}
