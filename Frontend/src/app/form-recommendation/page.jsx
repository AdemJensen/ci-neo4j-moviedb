'use client'

import {useState} from 'react'
import {apiService} from "@/lib/api-config";
import Markdown from 'react-markdown'
import Navbar from "@/components/ui/navbar";
import {Card, CardContent, CardHeader} from "@/components/ui/card";
import RasaChatWidget from "@/components/ui/RasaChatWidget";

export default function MovieRecommenderPage() {
    const [genre, setGenre] = useState('Any')
    const [country, setCountry] = useState('Any')
    const [language, setLanguage] = useState('Any')
    const [yearRange, setYearRange] = useState('Any')
    const [description, setDescription] = useState('')
    const [loading, setLoading] = useState(false)
    const [recommendation, setRecommendation] = useState('')

    const handleSubmit = async () => {
        setLoading(true)
        setRecommendation('')
        const res = await apiService.postData('/form-recommendations', {
            genre,
            country,
            language,
            year_range: yearRange,
            description
        })
        const data = await res.json()
        setRecommendation(data.recommendation)
        setLoading(false)
    }

    return (
        <div className="min-h-screen bg-gray-100">
            <Navbar/>
            <div className="p-8">
                <Card className="max-w-6xl mx-auto">
                    <CardHeader>
                            <div className="flex flex-col justify-between items-center">
                                <h1 className="text-4xl font-bold text-center text-red-600 mb-2">🎬 Movie Recommendation
                                    Assistant</h1>
                                <p className="text-center text-gray-600 italic mb-6">Discover the perfect movie tailored
                                    just for
                                    you.</p>
                            </div>
                        </CardHeader>
                    <div className="max-w-2xl mx-auto px-4">
                        <CardContent>
                            <div className="space-y-4">
                                <select value={genre} onChange={e => setGenre(e.target.value)}
                                        className="w-full p-2 border rounded">
                                    {['Any', 'Action', 'Romance', 'Sci-Fi', 'Comedy', 'Mystery', 'Documentary', 'Animation'].map(opt => (
                                        <option key={opt}>{opt}</option>
                                    ))}
                                </select>
                                <select value={country} onChange={e => setCountry(e.target.value)}
                                        className="w-full p-2 border rounded">
                                    {['Any', 'USA', 'China', 'Japan', 'France', 'South Korea', 'UK'].map(opt => (
                                        <option key={opt}>{opt}</option>
                                    ))}
                                </select>
                                <select value={language} onChange={e => setLanguage(e.target.value)}
                                        className="w-full p-2 border rounded">
                                    {['Any', 'English', 'Chinese', 'Japanese', 'Korean', 'French'].map(opt => (
                                        <option key={opt}>{opt}</option>
                                    ))}
                                </select>
                                <select value={yearRange} onChange={e => setYearRange(e.target.value)}
                                        className="w-full p-2 border rounded">
                                    {['Any', 'After 2020', '2010-2020', '2000-2010', 'Before 2000'].map(opt => (
                                        <option key={opt}>{opt}</option>
                                    ))}
                                </select>
                                <textarea
                                    value={description}
                                    onChange={e => setDescription(e.target.value)}
                                    className="w-full p-3 border rounded"
                                    rows={4}
                                    placeholder="Example: A feel-good romantic comedy set in Paris with a twist ending..."
                                ></textarea>
                                <div className="flex justify-center">
                                    <button
                                        onClick={handleSubmit}
                                        className="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 transition"
                                        disabled={loading}
                                    >
                                        {loading ? '🧠 Thinking...' : '✨ Recommend a Movie'}
                                    </button>
                                </div>
                            </div>

                            {recommendation && (
                                <div className="mt-6 bg-green-100 p-4 rounded border border-green-300">
                                    <h2 className="text-xl font-bold mb-2">🎥 Your Movie Recommendation</h2>
                                    <Markdown>
                                        {recommendation}
                                    </Markdown>
                                </div>
                            )}
                        </CardContent>
                    </div>
                </Card>
            </div>
            <RasaChatWidget />
        </div>
)
}
