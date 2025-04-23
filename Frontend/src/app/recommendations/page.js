"use client";

import {useEffect, useState} from 'react'
import Navbar from '@/components/ui/navbar'
import {Card, CardContent, CardHeader} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import {apiService} from "@/lib/api-config";
import {gotoAuthPage} from "@/lib/utils";
import {useRouter} from "next/navigation";
import RasaChatWidget from "@/components/ui/RasaChatWidget";

export default function RecommendationPage() {
    const router = useRouter();
    const [movies, setMovies] = useState([])
    const [loading, setLoading] = useState(false)
    const [started, setStarted] = useState(false)

    const handleGetRecommendations = async () => {
        setStarted(true)
        setLoading(true)

        const session_id = localStorage.getItem('tmdb_session_id')
        if (!session_id) {
            gotoAuthPage()
            return
        }

        try {
            apiService.fetchData(`/recommendations?session_id=${session_id}`)
                .then(res => res.json())
                .then(data => {
                    console.log('Favorites data:', data)
                    setMovies(data.results || [])
                    setLoading(false)
                })
        } catch (error) {
            console.error('Failed to fetch recommendations:', error)
            setLoading(false)
        }
    }

    const handleNavigation = (path) => {
        // router.push(path);
        // open in new tab
        window.open(path, '_blank');
    };

    return (
        <div className="min-h-screen bg-gray-100">
            <Navbar/>
            <div className="p-8">
                <Card className="max-w-6xl mx-auto">
                    <CardHeader>
                        <h1 className="text-2xl font-bold">🎯 Personalized Recommendation</h1>
                    </CardHeader>
                    <CardContent>
                        {!started && (
                            <div className="text-center space-y-6">
                                <p className="text-gray-700 text-lg">
                                    Click the button below to start your personalized recommendation using your TMDB
                                    favorite movies.
                                </p>
                                <Button onClick={handleGetRecommendations}
                                        className="bg-blue-600 text-white hover:bg-blue-700">
                                    Get my recommendation
                                </Button>
                                <p className="text-gray-700 text-lg">You can also try out our form-based
                                    recommendation.</p>
                                <Button variant="outline" onClick={() => window.location.href = '/form-recommendation'}>
                                    Go to form-based recommendation
                                </Button>
                            </div>
                        )}

                        {started && loading && (
                            <div className="flex flex-col justify-center items-center h-96">
                                <p className="text-gray-700 text-lg mb-4">Making recommendations, this may take a few seconds...</p>
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
                            </div>
                        )}

                        {!loading && movies.length > 0 && (
                            <div className="flex flex-col justify-center items-center">
                                <Button onClick={handleGetRecommendations}
                                        className="bg-blue-600 text-white hover:bg-blue-700">
                                    Get another set of recommendations
                                </Button>
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mt-5">
                                    {movies.map((movie) => (
                                        <Card key={movie.id} className="bg-white shadow hover:shadow-md transition cursor-pointer"
                                            onClick={() => handleNavigation(`/?q=${encodeURIComponent(movie.title)}&type=movie`)}>
                                            <CardContent className="p-4">
                                                {/*{movie.poster_path ? (*/}
                                                {/*    <img*/}
                                                {/*        src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}*/}
                                                {/*        alt={movie.title}*/}
                                                {/*        className="rounded w-full mb-3"*/}
                                                {/*    />*/}
                                                {/*) : (*/}
                                                {/*    <div className="bg-gray-200 h-64 rounded mb-3"/>*/}
                                                {/*)}*/}
                                                <h3 className="text-lg font-semibold">{movie.title}</h3>
                                                <p className="text-sm text-gray-500">{movie.release_date}</p>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
            <RasaChatWidget />
        </div>
    )
}
