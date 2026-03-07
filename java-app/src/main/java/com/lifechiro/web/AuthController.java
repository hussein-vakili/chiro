package com.lifechiro.web;

import com.lifechiro.auth.InvitationAcceptanceService;
import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.auth.model.PortalUserRecord;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolderStrategy;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
public class AuthController {
    private final InvitationAcceptanceService invitationAcceptanceService;
    private final SecurityContextRepository securityContextRepository;
    private final SecurityContextHolderStrategy securityContextHolderStrategy;

    public AuthController(
        InvitationAcceptanceService invitationAcceptanceService,
        SecurityContextRepository securityContextRepository,
        SecurityContextHolderStrategy securityContextHolderStrategy
    ) {
        this.invitationAcceptanceService = invitationAcceptanceService;
        this.securityContextRepository = securityContextRepository;
        this.securityContextHolderStrategy = securityContextHolderStrategy;
    }

    @GetMapping("/")
    public String root(Authentication authentication) {
        return authentication == null ? "redirect:/login" : "redirect:/dashboard";
    }

    @GetMapping("/login")
    public String login(
        Authentication authentication,
        @RequestParam(name = "error", required = false) String error,
        @RequestParam(name = "logout", required = false) String logout,
        Model model
    ) {
        if (isSignedIn(authentication)) {
            return "redirect:/dashboard";
        }
        model.addAttribute("loginError", error != null);
        model.addAttribute("loggedOut", logout != null);
        return "login";
    }

    @GetMapping("/invite/{token}")
    public String invite(@PathVariable String token, Authentication authentication, Model model) {
        if (isSignedIn(authentication)) {
            return "redirect:/dashboard";
        }
        populateInvitationModel(model, token);
        return "accept-invite";
    }

    @PostMapping("/invite/{token}")
    public String acceptInvite(
        @PathVariable String token,
        @RequestParam String password,
        @RequestParam(name = "confirm_password") String confirmPassword,
        HttpServletRequest request,
        HttpServletResponse response,
        RedirectAttributes redirectAttributes,
        Model model
    ) {
        InvitationAcceptanceService.AcceptanceResult result = invitationAcceptanceService.acceptInvitation(token, password, confirmPassword);
        if (!result.success()) {
            populateInvitationModel(model, token);
            model.addAttribute("errorMessage", result.errorMessage());
            return "accept-invite";
        }
        signIn(result.user(), request, response);
        redirectAttributes.addFlashAttribute("flashMessage", "Invitation accepted. Your Java portal account is ready.");
        return "redirect:/dashboard";
    }

    private void populateInvitationModel(Model model, String token) {
        InvitationAcceptanceService.InvitationViewModel view = invitationAcceptanceService.loadInvitation(token);
        model.addAttribute("invalid", view.invalid());
        model.addAttribute("invalidMessage", view.invalidMessage());
        model.addAttribute("invitation", view.invitation());
        model.addAttribute("slotHold", view.slotHold());
        model.addAttribute("reservedAppointmentLabel", view.reservedAppointmentLabel());
    }

    private void signIn(PortalUserRecord user, HttpServletRequest request, HttpServletResponse response) {
        PortalUserDetails principal = new PortalUserDetails(user);
        SecurityContext context = securityContextHolderStrategy.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities()));
        securityContextHolderStrategy.setContext(context);
        securityContextRepository.saveContext(context, request, response);
    }

    private boolean isSignedIn(Authentication authentication) {
        return authentication != null
            && authentication.isAuthenticated()
            && !(authentication instanceof AnonymousAuthenticationToken)
            && !"anonymousUser".equals(authentication.getPrincipal());
    }
}
