import { useEffect, useState } from "react"
import { getUserProjects } from "../client"
import type { Project } from "../types"

const HW_SET_1_RATE = 5   // $ per unit per month
const HW_SET_2_RATE = 10  // $ per unit per month

type ProjectHardware = {
    hw_set_1: number
    hw_set_2: number
}

type ProjectBilling = Project & {
    hw_set_1: number
    hw_set_2: number
    total: number
}

async function getProjectHardware(projectId: string): Promise<ProjectHardware> {
    const res = await fetch(`/api/projects/${projectId}/hardware`, {
        headers: { "Content-Type": "application/json" },
        credentials: "include",
    })
    if (!res.ok) throw new Error("Failed to fetch project hardware")
    return res.json()
}

export const Billing = () => {
    const [billingData, setBillingData] = useState<ProjectBilling[]>([])
    const [error, setError] = useState("")
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const load = async () => {
            setIsLoading(true)
            try {
                const projects = await getUserProjects()
                const rows = await Promise.all(
                    projects.map(async (p: Project) => {
                        try {
                            const hw = await getProjectHardware(p.id)
                            const total =
                                hw.hw_set_1 * HW_SET_1_RATE +
                                hw.hw_set_2 * HW_SET_2_RATE
                            return { ...p, ...hw, total }
                        } catch {
                            return { ...p, hw_set_1: 0, hw_set_2: 0, total: 0 }
                        }
                    })
                )
                setBillingData(rows)
            } catch {
                setError("Failed to load billing data")
            } finally {
                setIsLoading(false)
            }
        }
        load()
    }, [])

    const grandTotal = billingData.reduce((sum, p) => sum + p.total, 0)

    return (
        <div className="grow bg-[#333f48] text-white p-6 flex flex-col items-center gap-6">

            <span className="text-xl font-bold tracking-wide">Monthly Billing Summary</span>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded w-full max-w-4xl">
                    {error}
                </div>
            )}

            {isLoading ? (
                <div className="text-white opacity-70 mt-8">Loading billing data...</div>
            ) : billingData.length === 0 ? (
                <div className="text-white opacity-70 mt-8">No projects found.</div>
            ) : (
                <div className="w-full max-w-4xl flex flex-col gap-4">
                    <div className="flex gap-6 text-sm text-white/70 mb-2">
                        <span>
                            <span className="text-[#BF5700] font-bold">HW Set 1</span>
                            {" "}— ${HW_SET_1_RATE}/unit/month
                        </span>
                        <span>
                            <span className="text-[#BF5700] font-bold">HW Set 2</span>
                            {" "}— ${HW_SET_2_RATE}/unit/month
                        </span>
                    </div>
                    <table className="w-full border border-white text-sm">
                        <thead>
                            <tr className="bg-[#BF5700] text-white text-left">
                                <th className="border border-white px-4 py-3">Project ID</th>
                                <th className="border border-white px-4 py-3">Project Name</th>
                                <th className="border border-white px-4 py-3">Description</th>
                                <th className="border border-white px-4 py-3 text-center">HW Set 1 (qty)</th>
                                <th className="border border-white px-4 py-3 text-center">HW Set 2 (qty)</th>
                                <th className="border border-white px-4 py-3 text-right">Monthly Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {billingData.map((p, i) => (
                                <tr
                                    key={p.id}
                                    className={i % 2 === 0 ? "bg-[#2a3540]" : "bg-[#333f48]"}
                                >
                                    <td className="border border-white/30 px-4 py-3 font-mono text-[#BF5700]">
                                        {p.id}
                                    </td>
                                    <td className="border border-white/30 px-4 py-3 font-semibold">
                                        {p.name}
                                    </td>
                                    <td className="border border-white/30 px-4 py-3 text-white/70">
                                        {p.description}
                                    </td>
                                    <td className="border border-white/30 px-4 py-3 text-center">
                                        {p.hw_set_1}
                                    </td>
                                    <td className="border border-white/30 px-4 py-3 text-center">
                                        {p.hw_set_2}
                                    </td>
                                    <td className="border border-white/30 px-4 py-3 text-right font-bold text-green-400">
                                        ${p.total.toFixed(2)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                        <tfoot>
                            <tr className="bg-[#BF5700] font-bold">
                                <td colSpan={5} className="border border-white px-4 py-3 text-right">
                                    TOTAL MONTHLY COST
                                </td>
                                <td className="border border-white px-4 py-3 text-right text-white text-lg">
                                    ${grandTotal.toFixed(2)}
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            )}
        </div>
    )
}
