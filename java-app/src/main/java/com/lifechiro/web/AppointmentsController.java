package com.lifechiro.web;

import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.booking.PatientAppointmentsService;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
public class AppointmentsController {
    private final PatientAppointmentsService patientAppointmentsService;

    public AppointmentsController(PatientAppointmentsService patientAppointmentsService) {
        this.patientAppointmentsService = patientAppointmentsService;
    }

    @GetMapping("/appointments")
    public String appointments(
        @AuthenticationPrincipal PortalUserDetails principal,
        @RequestParam Map<String, String> queryParams,
        Model model
    ) {
        if (principal == null || !principal.isClient()) {
            return "redirect:/dashboard";
        }
        PatientAppointmentsService.AppointmentsPageModel page = patientAppointmentsService.buildPatientPage(principal, queryParams);
        model.addAttribute("principal", principal);
        model.addAttribute("page", page);
        return "appointments";
    }

    @PostMapping("/appointments/self-book")
    public String selfBook(
        @AuthenticationPrincipal PortalUserDetails principal,
        @RequestParam Map<String, String> formData,
        RedirectAttributes redirectAttributes
    ) {
        if (principal == null || !principal.isClient()) {
            return "redirect:/dashboard";
        }
        PatientAppointmentsService.BookingActionResult result = patientAppointmentsService.bookFromPortal(principal, formData);
        if (result.success()) {
            redirectAttributes.addFlashAttribute("flashMessage", result.message());
            if (result.redirectUrl() != null) {
                return "redirect:" + result.redirectUrl();
            }
        } else {
            redirectAttributes.addFlashAttribute("errorMessage", result.message());
        }
        Map<String, String> redirectParams = new LinkedHashMap<>();
        copyIfPresent(formData, redirectParams, "care_plan_visit_id");
        copyIfPresent(formData, redirectParams, "service_id");
        copyIfPresent(formData, redirectParams, "location_id");
        copyIfPresent(formData, redirectParams, "appointment_date");
        if ("any".equalsIgnoreCase(formData.getOrDefault("clinician_user_id", ""))) {
            redirectParams.put("clinician_user_id", "any");
        } else {
            copyIfPresent(formData, redirectParams, "clinician_user_id");
        }
        return redirectToAppointments(redirectParams);
    }

    @PostMapping("/appointments/{appointmentId}/cancel")
    public String cancel(
        @AuthenticationPrincipal PortalUserDetails principal,
        @PathVariable long appointmentId,
        RedirectAttributes redirectAttributes
    ) {
        if (principal == null || !principal.isClient()) {
            return "redirect:/dashboard";
        }
        PatientAppointmentsService.BookingActionResult result = patientAppointmentsService.cancelAppointment(principal, appointmentId);
        if (result.success()) {
            redirectAttributes.addFlashAttribute("flashMessage", result.message());
            if (result.redirectUrl() != null) {
                return "redirect:" + result.redirectUrl();
            }
        } else {
            redirectAttributes.addFlashAttribute("errorMessage", result.message());
        }
        return "redirect:/appointments";
    }

    private void copyIfPresent(Map<String, String> source, Map<String, String> target, String key) {
        String value = source.getOrDefault(key, "").trim();
        if (!value.isBlank()) {
            target.put(key, value);
        }
    }

    private String redirectToAppointments(Map<String, String> params) {
        if (params.isEmpty()) {
            return "redirect:/appointments";
        }
        StringBuilder builder = new StringBuilder("redirect:/appointments?");
        boolean first = true;
        for (Map.Entry<String, String> entry : params.entrySet()) {
            if (!first) {
                builder.append('&');
            }
            builder.append(entry.getKey()).append('=').append(entry.getValue());
            first = false;
        }
        return builder.toString();
    }
}
