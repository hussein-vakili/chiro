package com.lifechiro.web;

import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.careplan.CarePlanService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class CarePlanController {
    private final CarePlanService carePlanService;

    public CarePlanController(CarePlanService carePlanService) {
        this.carePlanService = carePlanService;
    }

    @GetMapping("/care-plan")
    public String carePlan(@AuthenticationPrincipal PortalUserDetails principal, Model model) {
        if (principal == null || !principal.isClient()) {
            return "redirect:/dashboard";
        }
        model.addAttribute("principal", principal);
        model.addAttribute("page", carePlanService.buildPatientPage(principal.user().id()));
        return "care-plan";
    }
}
