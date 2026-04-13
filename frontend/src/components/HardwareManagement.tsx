import React, { useEffect, useState } from "react"
import type { Hardware } from "../types"
import { getHardwareResources, getProjectHardwareResources, requestHardware, returnHardware } from "../client"

export const HardwareManagement = () => {

    const [hardwareState, setHardwareState] = useState<Hardware[]>([])
    const [projectId, setProjectId] = useState<string>("")
    const [projectHardwareState, setProjectHardwareState] = useState<Hardware[]>([])
    const [requestQuantities, setRequestQuantities] = useState<Record<string, number>>({})
    const [returnQuantities, setReturnQuantities] = useState<Record<string, number>>({})
    const [returnFormVisible, setReturnFormVisible] = useState<boolean>(false)

    const [message, setMessage] = useState("")
    const [error, setError] = useState("")
    const [isSubmitting, setIsSubmitting] = useState(false)

    useEffect(() => {
        if (!message && !error) return;
        const timer = setTimeout(() => {
            setMessage("");
            setError("");
        }, 5000);
        return () => clearTimeout(timer);
    }, [message, error]);

    useEffect(() => {
        getHardwareResources()
        .then(resp => {setHardwareState(resp)})
        .catch(() => setError("Failed to load Hardware Resources"))
    }, [])

    const onReturnVisible = async (e: React.FormEvent) => {
        e.preventDefault()
        getProjectHardwareResources(projectId)
        .then(resp => {setProjectHardwareState(resp)})
        .catch(() => setError("Failed to load current Project Hardware Resources"))
        setReturnQuantities({})
        setReturnFormVisible(!returnFormVisible)
    }

    const onRequestSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError("")
        setMessage("")
        setIsSubmitting(true)

        try {
            const requests = hardwareState.map((h) => ({
                set: h.set,
                quantity: requestQuantities[h.set] ?? 0,
            }))
            await requestHardware(projectId, requests)
            getHardwareResources().then(resp => setHardwareState(resp))
            setMessage("Hardware requested successfully")
        } catch (err: unknown) {
            const error = err as { response?: { data?: { error?: string } } };
            setError(error.response?.data?.error || 'Failed to request hardware')
        } finally {
            setIsSubmitting(false)
        }
    }

    const onReturnSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError("")
        setMessage("")
        setIsSubmitting(true)

        try {
            const returns = projectHardwareState.map((h) => ({
                set: h.set,
                quantity: returnQuantities[h.set] ?? 0,
            })).filter((r) => r.quantity > 0)

            if (returns.length === 0) {
                setError("Enter a return quantity greater than 0")
                return
            }

            await returnHardware(projectId, returns)
            getHardwareResources().then(resp => setHardwareState(resp))
            getProjectHardwareResources(projectId).then(resp => setProjectHardwareState(resp))
            setReturnQuantities({})
            setMessage("Hardware returned successfully")
        } catch (err: unknown) {
            const error = err as { response?: { data?: { error?: string } } };
            setError(error.response?.data?.error || 'Failed to return hardware')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="grow bg-[#333f48] text-white p-4 gap-4 items-center flex flex-col">

            {error && (
                <div data-testid="hardware-error" className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {message && (
                <div data-testid="hardware-message" className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                    {message}
                </div>
            )}

            <span className="text-xl font-bold">Hardware Resource Management</span>
            <div className="flex flex-col gap-2 items-center">
                <label className="text-sm">Project ID</label>
                <input
                    data-testid="hardware-project-id"
                    type="text"
                    className="border border-[#BF5700] p-2 bg-white text-black rounded"
                    placeholder="Enter Project ID"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                />
            </div>
            <table data-testid="hardware-table" className="border border-white">
                <thead>
                    <tr className="border border-white">
                        <th className="border border-white p-2">Name</th>
                        <th className="border border-white p-2">Capacity</th>
                        <th className="border border-white p-2">Available</th>
                        <th className="border border-white p-2">Request</th>
                    </tr>
                </thead>
                <tbody>
                    {hardwareState.map((h, index) => (
                        <tr key={h.set} className="border border-white">
                            <td className="border border-white p-2">{h.set}</td>
                            <td className="border border-white p-2">{h.capacity}</td>
                            <td className="border border-white p-2">{h.available}</td>
                            <input data-testid={`request-set${index + 1}`} type="number" className="border border-[#BF5700] p-2 bg-white text-black w-20 mx-auto" placeholder="0"
                                onChange={(e) => setRequestQuantities((prev) => ({ ...prev, [h.set]: Number(e.target.value) || 0 }))}/>
                        </tr>
                    ))}
                </tbody>
            </table>
            <button data-testid="hardware-submit-request" className="flex bg-[#BF5700] text-white p-2 rounded cursor-pointer font-bold mt-4 disabled:opacity-60 disabled:cursor-not-allowed" onClick={onRequestSubmit} disabled={isSubmitting}>
                SUBMIT REQUEST
            </button>
            <button data-testid="hardware-return-btn" className="flex bg-[#BF5700] text-white p-2 rounded cursor-pointer font-bold mt-4 disabled:opacity-60 disabled:cursor-not-allowed" onClick={onReturnVisible} disabled={isSubmitting}>
                RETURN EQUIPMENT
            </button>
            {returnFormVisible &&
                <div data-testid="hardware-return-form" className="flex flex-col gap-4 bg-white  text-black p-4 rounded">
                    <table data-testid="hardware-return-table" className="border border-black">
                        <thead>
                            <tr className="border border-black">
                                <th className="border border-black p-2">Name</th>
                                <th className="border border-black p-2">Checked Out</th>
                                <th className="border border-black p-2">Return</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projectHardwareState.map((h, index) => (
                                <tr key={h.set} className="border border-black">
                                    <td className="border border-black p-2">{h.set}</td>
                                    <td className="border border-black p-2">{h.checkedOut}</td>
                                    <input data-testid={`return-set${index + 1}`} type="number" className="border border-[#BF5700] p-2 bg-white text-black w-20 mx-auto" placeholder="0"
                                        onChange={(e) => setReturnQuantities((prev) => ({ ...prev, [h.set]: Number(e.target.value) || 0 }))}/>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <button data-testid="hardware-return-submit" className="flex bg-[#BF5700] text-white p-2 rounded cursor-pointer font-bold text-center mx-auto disabled:opacity-60 disabled:cursor-not-allowed" onClick={onReturnSubmit} disabled={isSubmitting}>
                        SUBMIT
                    </button>
                </div>
            }
        </div>
    )
}