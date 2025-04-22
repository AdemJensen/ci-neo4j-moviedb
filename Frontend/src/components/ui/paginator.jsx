'use client'

import { Button } from "@/components/ui/button"

export default function Paginator({ page, total, size, onPageChange }) {
  const totalPages = Math.ceil(total / size)

  if (totalPages <= 1) return null

  return (
    <div className="flex justify-center items-center gap-4 mt-6">
      <Button
        variant="outline"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>

      <span className="text-sm text-gray-600">
        Page {page} of {totalPages}
      </span>

      <Button
        variant="outline"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </div>
  )
}
