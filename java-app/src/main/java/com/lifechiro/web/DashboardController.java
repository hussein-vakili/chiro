package com.lifechiro.web;

import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.careplan.CarePlanService;
import com.lifechiro.dashboard.DashboardService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class DashboardController {
    private final DashboardService dashboardService;
    private final CarePlanService carePlanService;

    public DashboardController(DashboardService dashboardService, CarePlanService carePlanService) {
        this.dashboardService = dashboardService;
        this.carePlanService = carePlanService;
    }

    @GetMapping("/dashboard")
    public String dashboard(@AuthenticationPrincipal PortalUserDetails principal, Model model) {
        model.addAttribute("principal", principal);
        model.addAttribute("summary", dashboardService.buildSummary(principal));
        if (principal != null && principal.isClient()) {
            model.addAttribute("carePlan", carePlanService.buildPatientPage(principal.user().id()));
        }
        return "dashboard";
    }
}
