
# To learn more about how to use Nix to configure your environment
# see: https://firebase.google.com/docs/studio/customize-workspace
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.11"; # or "unstable"

  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.uv
    pkgs.gnumake
    pkgs.terraform
    pkgs.gh
  ];
  # Sets environment variables in the workspace
  env = {};
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
    ];
    workspace = {
      # Runs when a workspace is first created with this `dev.nix` file
      onCreate = {
        create-venv = ''
        # Load environment variables from .env file if it exists
        source .env

        # Beautiful prints for gcloud setup
        echo ""
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║                  🔐 GCLOUD SETUP REQUIRED                  ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        echo "📝 Before proceeding, please ensure:"
        echo "   1️⃣  You are logged in to gcloud"
        echo "   2️⃣  You have selected the correct project"
        echo ""

        auth_status=$(gcloud auth list --quiet 2>&1)

        echo ""
        echo "⚙️  We will now set the project you want to use..."
        gcloud config get project

        echo ""
        echo "💡 Need to setup? Run these commands:"
        echo "   → gcloud auth login"
        echo "   → gcloud config set project YOUR_PROJECT_ID"
        echo ""

        echo "Running agent starter pack creation..."
        echo adk@$AGENT_NAME
        uvx agent-starter-pack create $AGENT_NAME -ag -a adk@$AGENT_NAME -d agent_engine --region $REGION --auto-approve
        code ~/$WS_NAME/$AGENT_NAME/README.md
        exec bash
        '';
        # Open editors for the following files by default, if they exist:
        default.openFiles = [];
      };
      # To run something each time the workspace is (re)started, use the `onStart` hook
    };
    # Enable previews and customize configuration
    previews = {};
  };
}