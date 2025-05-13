# No user-configurable parameters
# Accept additional arguments to this template corresponding to template
# parameter IDs
{ pkgs, agent_name ? "", google_cloud_project_id ? "", ... }: {
  # Shell script that produces the final environment
  bootstrap = ''
    # Copy the folder containing the `idx-template` files to the final
    # project folder for the new workspace. ${./.} inserts the directory
    # of the checked-out Git folder containing this template.
    cp -rf ${./.} "$out"

    # Set some permissions
    chmod -R +w "$out"

    # Create .env file with the parameter values
    cat > "$out/.env" << EOF
    AGENT_NAME=${agent_name}
    GOOGLE_CLOUD_PROJECT=${google_cloud_project_id}
    WS_NAME=$WS_NAME
    EOF

    # Remove the template files themselves and any connection to the template's
    # Git repository
    rm -rf "$out/.git" "$out/idx-template".{nix,json}
  '';
}
