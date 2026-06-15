/***
 * Copyright (2023) Hewlett Packard Enterprise Development LP
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * You may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ***/

import React, { useState } from "react";
import FastAPIClient from "../../client";
import config from "../../config";
import DashboardHeader from "../../components/DashboardHeader";
import Footer from "../../components/Footer";

const client = new FastAPIClient(config);

const Search = () => {
    const [nlpQuestion, setNlpQuestion] = useState("");
    const [nlpLoading, setNlpLoading] = useState(false);
    const [nlpLog, setNlpLog] = useState([]);
    const [nlpResults, setNlpResults] = useState(null);

    const handleNlpSearch = async () => {
        const q = nlpQuestion.trim();
        if (!q) return;
        setNlpLoading(true);
        setNlpResults(null);
        const ts = new Date().toLocaleTimeString();
        console.log(`[NLP Query] ${ts} — Question: ${q}`);
        try {
            const result = await client.nlpQuery(q);
            console.log(`[NLP Query] ${ts} — SQL: ${result.sql_query}`);
            const rows = Array.isArray(result.results) ? result.results : [];
            const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
            setNlpLog(prev => [{ question: q, sql: result.sql_query, ts, error: null }, ...prev]);
            setNlpResults({
                columns,
                rows,
                row_count: rows.length,
                error: null,
                sql: result.sql_query,
                ai_response: result.ai_response || "",
            });
        } catch (err) {
            const errMsg = err?.response?.data?.detail || err.message || "Unknown error";
            console.error(`[NLP Query] ${ts} — Error: ${errMsg}`);
            setNlpLog(prev => [{ question: q, sql: null, ts, error: errMsg }, ...prev]);
            setNlpResults({ error: errMsg, columns: [], rows: [], row_count: 0, sql: null });
        } finally {
            setNlpLoading(false);
            setNlpQuestion("");
        }
    };

    return (
        <section className="flex flex-col bg-white min-h-screen">
            <DashboardHeader />
            <div className="flex-grow px-8 py-8 max-w-5xl mx-auto w-full">
                {/* Page Title */}
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900 mb-1">AI Search</h1>
                    <p className="text-sm text-gray-500">Ask questions in plain English — queries run directly against the MLMD database.</p>
                </div>

                {/* Search Bar */}
                <div className="flex items-center gap-2 mb-4">
                    <div className="relative flex-grow">
                        <input
                            type="text"
                            value={nlpQuestion}
                            onChange={(e) => setNlpQuestion(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && !nlpLoading && handleNlpSearch()}
                            placeholder="e.g. Show all artifacts with accuracy above 0.9, how many pipelines exist..."
                            className="w-full px-4 py-3 pl-10 border border-violet-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 shadow-sm text-sm"
                        />
                        <svg className="absolute left-3 top-3.5 w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
                        </svg>
                    </div>
                    <button
                        onClick={handleNlpSearch}
                        disabled={nlpLoading || !nlpQuestion.trim()}
                        className={`px-6 py-3 rounded-lg text-sm font-semibold transition-all shadow-sm flex items-center gap-2 ${nlpLoading || !nlpQuestion.trim() ? 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed' : 'bg-violet-600 text-white hover:bg-violet-700'}`}
                    >
                        {nlpLoading ? (
                            <>
                                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                </svg>
                                Thinking...
                            </>
                        ) : "Ask AI"}
                    </button>
                    {nlpLog.length > 0 && (
                        <button onClick={() => { setNlpLog([]); setNlpResults(null); }} className="text-xs text-gray-400 hover:text-gray-600 px-2">Clear</button>
                    )}
                </div>

                {/* Console Panel */}
                {nlpLog.length > 0 && (
                    <div className="mb-4 rounded-lg border border-gray-800 bg-gray-950 text-xs font-mono overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
                            <span className="text-gray-400 font-sans font-medium text-xs tracking-wide">AI QUERY CONSOLE</span>
                            <span className="text-gray-600 text-xs">{nlpLog.length} {nlpLog.length === 1 ? "query" : "queries"}</span>
                        </div>
                        <div className="max-h-48 overflow-y-auto divide-y divide-gray-800">
                            {nlpLog.map((entry, i) => (
                                <div key={i} className="px-4 py-3 space-y-1.5">
                                    <div className="flex items-start gap-2">
                                        <span className="text-violet-400 shrink-0">▶</span>
                                        <span className="text-gray-300">{entry.question}</span>
                                        <span className="ml-auto text-gray-600 shrink-0">{entry.ts}</span>
                                    </div>
                                    {entry.error ? (
                                        <div className="flex items-start gap-2 pl-4">
                                            <span className="text-red-400 shrink-0">✕</span>
                                            <span className="text-red-400">{entry.error}</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-start gap-2 pl-4">
                                            <span className="text-green-400 shrink-0">SQL</span>
                                            <span className="text-green-300 break-all">{entry.sql}</span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Results Panel */}
                {nlpResults && (
                    <div className="rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                        {/* Results header */}
                        <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-200">
                            <div className="flex items-center gap-3">
                                <span className={`text-xs font-semibold tracking-wide ${nlpResults.error ? "text-red-600" : "text-gray-700"}`}>
                                    {nlpResults.error ? "ERROR" : `${nlpResults.row_count} row${nlpResults.row_count !== 1 ? "s" : ""} returned`}
                                </span>
                                {nlpResults.sql && !nlpResults.error && (
                                    <span className="hidden sm:inline text-gray-400 text-xs font-mono truncate max-w-sm" title={nlpResults.sql}>
                                        {nlpResults.sql}
                                    </span>
                                )}
                            </div>
                            <button onClick={() => setNlpResults(null)} className="text-gray-400 hover:text-gray-600 text-lg leading-none ml-2">✕</button>
                        </div>

                        {/* Error state */}
                        {nlpResults.error ? (
                            <div className="px-4 py-4 bg-red-50">
                                <p className="text-xs font-mono text-red-600 whitespace-pre-wrap">{nlpResults.error}</p>
                            </div>

                            /* Empty state */
                        ) : nlpResults.rows.length === 0 ? (
                            <div className="px-4 py-6 text-center text-sm text-gray-400 italic">No rows returned.</div>

                            /* Table */
                        ) : (
                            <div className="overflow-x-auto max-h-96 overflow-y-auto">
                                <table className="min-w-full text-xs divide-y divide-gray-200">
                                    <thead className="bg-gray-50 sticky top-0 z-10">
                                        <tr>
                                            {nlpResults.columns.map((col) => (
                                                <th
                                                    key={col}
                                                    className="px-4 py-2.5 text-left font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap border-b border-gray-200"
                                                >
                                                    {col}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-100">
                                        {nlpResults.rows.map((row, i) => (
                                            <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                                                {nlpResults.columns.map((col) => (
                                                    <td
                                                        key={col}
                                                        className="px-4 py-2.5 text-gray-800 font-mono whitespace-nowrap max-w-xs truncate"
                                                        title={row[col] != null ? String(row[col]) : ""}
                                                    >
                                                        {row[col] != null ? String(row[col]) : <span className="text-gray-300 italic">null</span>}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* AI narrative response */}
                        {nlpResults.ai_response && !nlpResults.error && (
                            <div className="px-4 py-3 bg-violet-50 border-t border-violet-100 text-xs text-violet-800">
                                <span className="font-semibold mr-1">AI:</span>{nlpResults.ai_response}
                            </div>
                        )}
                    </div>
                )}
            </div>
            <Footer />
        </section>
    );
};

export default Search;
