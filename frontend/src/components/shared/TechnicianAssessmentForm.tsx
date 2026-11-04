import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { notifications } from "@/lib/notifications";

const assessmentSchema = z.object({
    assessment: z.enum(["passed", "failed", "attention"], {
        error: "Select an assessment.",
    }),
    defectDescription: z.string().trim().max(2000, "Use 2,000 characters or fewer."),
    notes: z.string().trim().max(2000, "Use 2,000 characters or fewer."),
}).superRefine((value, context) => {
    if (value.assessment !== "passed" && !value.defectDescription) {
        context.addIssue({
            code: "custom",
            path: ["defectDescription"],
            message: "Describe the defect or attention required.",
        });
    }
});

export type TechnicianAssessmentValues = z.infer<typeof assessmentSchema>;

export function TechnicianAssessmentForm({ onSave }: {
    onSave: (values: TechnicianAssessmentValues) => Promise<void>;
}) {
    const [saveError, setSaveError] = useState("");
    const {
        register,
        handleSubmit,
        watch,
        formState: { errors, isSubmitting },
    } = useForm<TechnicianAssessmentValues>({
        resolver: zodResolver(assessmentSchema),
        defaultValues: {
            defectDescription: "",
            notes: "",
        },
    });
    const assessment = watch("assessment");

    async function submit(values: TechnicianAssessmentValues) {
        setSaveError("");
        try {
            await onSave(values);
            notifications.success("Technician assessment saved.");
        } catch {
            setSaveError("Assessment could not be saved. Check the connection and try again.");
            notifications.error("Technician assessment could not be saved.");
        }
    }

    return (
        <form className="technician-assessment-form" onSubmit={handleSubmit(submit)} noValidate>
            <fieldset>
                <legend>Assessment <span aria-hidden="true">*</span></legend>
                {([
                    ["passed", "Passed"],
                    ["failed", "Failed"],
                    ["attention", "Attention required"],
                ] as const).map(([value, label]) => (
                    <label className="technician-assessment-option" key={value}>
                        <input type="radio" value={value} {...register("assessment")} />
                        {label}
                    </label>
                ))}
                {errors.assessment && <span className="form-field-error" role="alert">{errors.assessment.message}</span>}
            </fieldset>
            {(assessment === "failed" || assessment === "attention") && (
                <label className="form-field">
                    <span>Defect description <span aria-hidden="true">*</span></span>
                    <Textarea
                        rows={3}
                        aria-invalid={Boolean(errors.defectDescription)}
                        aria-describedby={errors.defectDescription ? "assessment-defect-error" : undefined}
                        {...register("defectDescription")}
                    />
                    {errors.defectDescription && <span id="assessment-defect-error" className="form-field-error" role="alert">{errors.defectDescription.message}</span>}
                </label>
            )}
            <label className="form-field">
                <span>Technician notes <span className="optional-field-mark">(optional)</span></span>
                <Textarea rows={3} aria-invalid={Boolean(errors.notes)} {...register("notes")} />
                {errors.notes && <span className="form-field-error" role="alert">{errors.notes.message}</span>}
            </label>
            {saveError && <p className="form-save-error" role="alert">{saveError}</p>}
            <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Saving…" : "Save assessment"}
            </Button>
        </form>
    );
}
